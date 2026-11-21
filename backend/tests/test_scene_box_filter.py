"""Sentetik kutular/sahte modeller: scene filtresi, adaptive ve route regression."""

from copy import deepcopy
from io import BytesIO
from math import sqrt
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import main
from backend.app.config import ADAPTIVE_THRESHOLDS, SceneBoxFilterSettings
from backend.app.models.base_detector import BaseDetector
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.services.inference_orchestrator import run_detection
from backend.app.services.query_processor import process_query
from backend.app.utils.scene_box_filter import filter_scene_boxes, scene_box_rule
from backend.tests.test_inventory_queries import translator
from backend.tests import legacy_adaptive


def setUpModule():
    # Eski eşik düşürme/yedek davranışı ayar olarak sınanır.
    legacy_adaptive.start()


def tearDownModule():
    legacy_adaptive.stop()


def detection(coords, query="backpack", confidence=.9):
    return {"label": query, "model_query": query, "confidence": confidence,
            "box": dict(zip(("xmin", "ymin", "xmax", "ymax"), coords))}


SCENE = detection((10, 10, 990, 990), confidence=.99)  # %96.04, dört kenara yakın.
NORMAL = detection((200, 200, 800, 900))  # %42, normal büyük nesne.


class SceneDetector(BaseDetector):
    name = response_model = "OWL-ViT"

    def __init__(self, model="owlvit", scene_only_first=False, scene_only_always=False):
        self.model_id = model
        self.response_model = "OWL-ViT" if model == "owlvit" else "grounding-dino"
        self.calls = []
        self.scene_only_first, self.scene_only_always = scene_only_first, scene_only_always

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.calls.append((list(queries), threshold, text_threshold))
        output = []
        for query in queries:
            if query == "backpack":
                output.append(deepcopy(SCENE))
                first = threshold == ADAPTIVE_THRESHOLDS[self.model_id].thresholds[0]
                if not self.scene_only_always and not (self.scene_only_first and first):
                    output.extend([deepcopy(NORMAL), {**deepcopy(NORMAL), "confidence": .8}])
            elif query == "bottle":
                output.append(detection((10, 400, 100, 700), "bottle"))
        return output

    def _infer_raw(self, image, queries, threshold):
        return self.infer_queries(image, queries, threshold)


class SceneBoxFilterTests(unittest.TestCase):
    def test_only_full_scene_box_is_removed_without_mutating_input(self):
        ordinary = [NORMAL, detection((100, 100, 850, 850)),
                    detection((0, 0, 950, 950)),  # %90.25 ama sadece iki kenar.
                    detection((0, 35, 969, 965))]  # %90.117 ama sadece sol kenar.
        records = [SCENE, *ordinary]
        before = deepcopy(records)
        kept, removed = filter_scene_boxes(records, (1000, 1000))
        self.assertEqual(kept, ordinary)
        self.assertEqual(records, before)
        self.assertEqual(len(removed), 1)
        self.assertAlmostEqual(removed[0]["area_ratio"], .9604)
        self.assertEqual(set(removed[0]["near_borders"]), {"left", "right", "top", "bottom"})
        self.assertEqual(removed[0]["reason"], "oversized_scene_box")

    def test_three_borders_area_threshold_and_resolution_independence(self):
        self.assertEqual(len(filter_scene_boxes([detection((0, 0, 1000, 900))], (1000, 1000))[1]), 1)
        # %89 + üç kenar fakat iki eksen de %97 altında: C de sağlanmaz.
        kept, _ = filter_scene_boxes([detection((30, 0, 970, 890000 / 940))], (1000, 1000))
        self.assertEqual(len(kept), 1)
        for width, height in ((1000, 1000), (2000, 800), (100, 50)):
            item = detection((width * .01, height * .01, width * .99, height * .99))
            self.assertAlmostEqual(filter_scene_boxes([item], (width, height))[1][0]["area_ratio"], .9604)

    def test_real_backpack_coordinates_match_rule_c_and_coverage_is_correct(self):
        item = detection((3.15, 267.01, 1532.93, 2035.66))
        diagnostics = []
        kept, removed = filter_scene_boxes([item], (1536, 2048), diagnostics=diagnostics)
        self.assertEqual(kept, [])
        entry = removed[0]
        self.assertEqual(entry["matched_rule"], "rule_c")
        self.assertAlmostEqual(entry["width_coverage"], 1529.78 / 1536)
        self.assertAlmostEqual(entry["height_coverage"], 1768.65 / 2048)
        self.assertAlmostEqual(entry["area_ratio"], entry["width_coverage"] * entry["height_coverage"])
        self.assertAlmostEqual(entry["area_ratio"], .8601, places=4)
        self.assertEqual(entry["touched_edges"], 3)
        self.assertEqual(set(entry["near_borders"]), {"left", "right", "bottom"})
        # C simetriktir: görüntü/kutu eksenleri değişirse yine aynı karar verilir.
        transposed = detection((267.01, 3.15, 2035.66, 1532.93))
        self.assertEqual(filter_scene_boxes([transposed], (2048, 1536))[1][0]["matched_rule"], "rule_c")

    def test_rule_c_requires_every_condition_and_preserves_a_b_precedence(self):
        cases = [(.86, 3, .995, .86 / .995, "rule_c"),
                 (.86, 3, .74, .86 / .74, None),  # Model kutusu görüntü dışına taşabilir.
                 (.70, 3, 1.0, .70, None),
                 (.86, 2, 1.0, .86, None),
                 (.86, 3, .95, .86 / .95, None),
                 (.90, 3, 1.0, .90, "rule_a"),
                 (.8836, 4, .94, .94, "rule_b")]
        for area, edges, width, height, expected in cases:
            with self.subTest(area=area, edges=edges, width=width, height=height):
                self.assertEqual(scene_box_rule(area, edges, width_coverage=width,
                                                height_coverage=height), expected)
        normal = detection((0, 0, 1000, 700))
        self.assertEqual(filter_scene_boxes([normal], (1000, 1000))[0], [normal])
        narrow = detection((0, 0, 740, .86 * 1000000 / 740))
        self.assertEqual(filter_scene_boxes([narrow], (1000, 1000))[0], [narrow])

    def test_rule_c_scene_only_returns_zero_for_both_models(self):
        with patch(__name__ + ".SCENE", detection((3.15, 267.01, 1532.93, 2035.66))):
            for model in ("owlvit", "grounding-dino"):
                detector = SceneDetector(model, scene_only_always=True)
                with Image.new("RGB", (1536, 2048)) as image:
                    result = run_detection(detector, image, process_query("backpack", translator()))
                self.assertEqual(result["inventory_summary"], {"backpack": 0})
                self.assertEqual(result["detections"], [])
                self.assertEqual(result["threshold_selection_reason"], "no_detections")
                self.assertEqual(len(detector.calls), len(ADAPTIVE_THRESHOLDS[model].thresholds))
                self.assertTrue(all(entry["matched_rule"] == "rule_c" for entry in result["scene_box_diagnostics"]))

    def test_two_tier_rule_truth_table(self):
        for area, edges, expected in ((.85, 4, "rule_b"), (.85, 2, None), (.65, 4, None),
                                      (.90, 3, "rule_a"), (.80, 4, "rule_b"), (.7999, 4, None),
                                      (.95, 2, None), (.85, 3, None)):
            with self.subTest(area=area, edges=edges):
                self.assertEqual(scene_box_rule(area, edges), expected)

    def test_geometry_and_both_kept_removed_diagnostics(self):
        # %85 dört-kenar örneği %3 toleransla geometrik olarak mümkün değildir.
        # %5 yalnızca bu sentetik testin config'i; production %3 olarak korunur.
        side = sqrt(.85) * 1000
        margin = (1000 - side) / 2
        centered = detection((margin, margin, 1000 - margin, 1000 - margin))
        anchored = detection((0, 0, side, side))
        diagnostics = []
        kept, removed = filter_scene_boxes([centered, anchored], (1000, 1000),
                                           SceneBoxFilterSettings(border_tolerance_ratio=.05), diagnostics=diagnostics)
        self.assertEqual(kept, [anchored])
        self.assertAlmostEqual(removed[0]["area_ratio"], .85)
        self.assertEqual(removed[0]["touched_edges"], 4)
        self.assertEqual(removed[0]["matched_rule"], "rule_b")
        self.assertEqual(diagnostics[1]["touched_edges"], 2)
        self.assertFalse(diagnostics[1]["removed"])
        # %65 + dört kenar kural testi de üretim toleransını değiştirmez.
        margin65 = (1 - sqrt(.65)) * 500
        small = detection((margin65, margin65, 1000 - margin65, 1000 - margin65))
        debug65 = []
        self.assertEqual(filter_scene_boxes([small], (1000, 1000),
                         SceneBoxFilterSettings(border_tolerance_ratio=.10), diagnostics=debug65)[0], [small])
        self.assertEqual(debug65[0]["touched_edges"], 4)
        # Gerçek default ölçüm: %85 merkez kutusu dört kenara %3 yakın değildir.
        default_debug = []
        self.assertEqual(filter_scene_boxes([centered], (1000, 1000), diagnostics=default_debug)[0], [centered])
        self.assertEqual(default_debug[0]["touched_edges"], 0)
        self.assertAlmostEqual(default_debug[0]["edge_distance_ratios"]["left"], margin / 1000)
        # Default'ta yeni B kuralının gerçekten devreye girdiği alan: %88.36.
        kept, removed = filter_scene_boxes([detection((30, 30, 970, 970))], (1000, 1000))
        self.assertEqual(kept, [])
        self.assertEqual(removed[0]["matched_rule"], "rule_b")
        self.assertAlmostEqual(removed[0]["area_ratio"], .8836)

    def test_invalid_geometry_not_hidden_and_settings_are_validated(self):
        invalid = detection((10, 10, 5, 5))
        self.assertEqual(filter_scene_boxes([invalid], (1000, 1000))[0], [invalid])
        invalid_score = {**SCENE, "confidence": float("nan")}
        kept, removed = filter_scene_boxes([invalid_score], (1000, 1000))
        self.assertIs(kept[0], invalid_score)
        self.assertEqual(removed, [])
        for size in ((0, 100), (-1, 100)):
            with self.assertRaises(ValueError):
                filter_scene_boxes([], size)
        for kwargs in ({"min_area_ratio": 0}, {"min_area_ratio": float("nan")},
                       {"border_tolerance_ratio": .5}, {"min_near_borders": 5},
                       {"full_scene_min_area_ratio": 0}, {"full_scene_min_area_ratio": .95},
                       {"full_scene_near_borders": 3}, {"axis_scene_min_area_ratio": 0},
                       {"axis_scene_min_near_borders": 5}, {"axis_scene_long_coverage": 1.1},
                       {"axis_scene_short_coverage": .99}):
            with self.assertRaises(ValueError):
                SceneBoxFilterSettings(**kwargs)

    def test_both_models_nms_then_scene_filter_then_inventory(self):
        for model in ("owlvit", "grounding-dino"):
            with Image.new("RGB", (1000, 1000)) as image:
                result = run_detection(SceneDetector(model), image, process_query("backpack", translator()))
            self.assertEqual(result["raw_detection_count"], 3)
            self.assertEqual(result["filtered_detection_count"], 1)
            self.assertEqual(result["inventory_summary"], {"backpack": 1})
            self.assertEqual(result["total_detected_objects"], 1)
            self.assertEqual(result["threshold_attempts"][0]["nms_detection_count"], 2)
            self.assertEqual(result["threshold_attempts"][0]["filtered_detection_count"], 1)
            # Scene filtresindeki kaldırma duplicate oranına eklenmez.
            self.assertAlmostEqual(result["threshold_attempts"][0]["duplicate_fraction"], 1/3)
            self.assertEqual(result["oversized_boxes_removed_count"], 1)
            self.assertEqual(result["oversized_boxes_removed"][0]["canonical_query"], "backpack")

    def test_scene_only_result_cannot_stop_adaptive_threshold_early(self):
        for model in ("owlvit", "grounding-dino"):
            detector = SceneDetector(model, scene_only_first=True)
            with Image.new("RGB", (1000, 1000)) as image:
                result = run_detection(detector, image, process_query("backpack", translator()))
            policy = ADAPTIVE_THRESHOLDS[model]
            self.assertEqual([call[1] for call in detector.calls], list(policy.thresholds[:2]))
            self.assertEqual(result["adaptive_threshold_used"], policy.thresholds[1])
            self.assertEqual(result["threshold_attempts"][0]["assessment"], "empty")
            self.assertEqual(result["threshold_selection_reason"], "first_valid_result")
            self.assertEqual(result["oversized_boxes_removed_count"], 2)  # İki ayrı denemenin kaydı.

    def test_all_scene_boxes_leave_zero_inventory_and_multi_query_diagnostics_survive(self):
        for model in ("owlvit", "grounding-dino"):
            with Image.new("RGB", (1000, 1000)) as image:
                single = run_detection(SceneDetector(model, scene_only_always=True), image, process_query("backpack", translator()))
                multi = run_detection(SceneDetector(model, scene_only_always=True), image, process_query("backpack, bottle", translator()))
            self.assertEqual(single["inventory_summary"], {"backpack": 0})
            self.assertEqual(single["threshold_selection_reason"], "no_detections")
            self.assertEqual(single["total_detected_objects"], 0)
            self.assertEqual(multi["inventory_summary"], {"backpack": 0, "bottle": 1})
            self.assertEqual(multi["total_detected_objects"], 1)
            self.assertEqual(multi["oversized_boxes_removed_count"], len(ADAPTIVE_THRESHOLDS[model].thresholds))
            self.assertTrue(all(d["canonical_query"] == "backpack" for d in multi["oversized_boxes_removed"]))

    def test_rule_b_both_models_can_return_zero_without_forcing_scene_result(self):
        with patch(__name__ + ".SCENE", detection((30, 30, 970, 970))):
            for model in ("owlvit", "grounding-dino"):
                detector = SceneDetector(model, scene_only_always=True)
                with Image.new("RGB", (1000, 1000)) as image:
                    result = run_detection(detector, image, process_query("backpack", translator()))
                self.assertEqual(result["inventory_summary"], {"backpack": 0})
                self.assertEqual(result["detections"], [])
                self.assertEqual(result["threshold_selection_reason"], "no_detections")
                self.assertEqual(len(detector.calls), len(ADAPTIVE_THRESHOLDS[model].thresholds))
                self.assertTrue(all(entry["matched_rule"] == "rule_b" for entry in result["scene_box_diagnostics"]))

    def test_http_json_jpeg_share_filtered_boxes_but_raw_debug_remains_raw(self):
        services = {model: SceneDetector(model) for model in ("owlvit", "grounding-dino")}
        registry = DetectorRegistry({key: lambda service=service: service for key, service in services.items()})
        with patch.object(main, "TranslationService", return_value=translator()), \
                patch.object(main, "DetectorRegistry", return_value=registry), TestClient(main.app) as client:
            with Image.new("RGB", (1000, 1000)) as image, BytesIO() as buffer:
                image.save(buffer, format="PNG")
                content = buffer.getvalue()
            for model in services:
                with patch.object(main, "annotate_image", wraps=main.annotate_image) as draw:
                    def post(endpoint, include=False):
                        response = client.post(endpoint, data={"query": "backpack", "model": model, "include_image": str(include).lower()},
                                               files={"image": ("scene.png", content, "image/png")})
                        self.assertEqual(response.status_code, 200)
                        return response
                    body = post("/detect", True).json()
                    self.assertEqual(len(draw.call_args.args[1]), 1)
                    self.assertEqual(body["oversized_boxes_removed_count"], 1)
                    self.assertAlmostEqual(body["oversized_boxes_removed"][0]["area_ratio"], .9604)
                    diagnostics = body["scene_box_diagnostics"]
                    self.assertEqual(len(diagnostics), 2)
                    self.assertEqual([entry["removed"] for entry in diagnostics], [True, False])
                    self.assertEqual(diagnostics[0]["touched_edges"], 4)
                    self.assertEqual(diagnostics[0]["edge_distance_ratios"]["left"], .01)
                    self.assertEqual(diagnostics[0]["image_size"], {"width": 1000, "height": 1000})
                    self.assertAlmostEqual(diagnostics[0]["box_area"] / diagnostics[0]["image_area"], .9604)
                    post("/detect-image")
                    self.assertEqual(len(draw.call_args.args[1]), 1)
                    post("/detect-raw-image")
                    self.assertEqual(len(draw.call_args.args[1]), 3)


if __name__ == "__main__":
    unittest.main()
