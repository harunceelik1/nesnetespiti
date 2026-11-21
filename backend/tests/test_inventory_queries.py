"""Gerçek ortak pipeline + sahte modeller; ağ/model yükleme/TCP sunucusu yok."""

from base64 import b64decode
from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import main
from backend.app.config import ADAPTIVE_THRESHOLDS
from backend.app.models.base_detector import BaseDetector
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.services.inference_orchestrator import run_detection
from backend.app.services.query_processor import process_query
from backend.app.services.translation_service import TranslationService, TranslationServiceError
from backend.tests import legacy_adaptive


# Bu dosya Marian model çeviri yolunu sınar; Türkçe nesne sözlüğü devre dışı bırakılır.
_lexicon_patch = patch("backend.app.services.object_lexicon.lookup", return_value=None)


def setUpModule():
    legacy_adaptive.start()
    _lexicon_patch.start()


def tearDownModule():
    legacy_adaptive.stop()
    _lexicon_patch.stop()


def translator():
    service = TranslationService.__new__(TranslationService)
    service.detect_language = lambda text: "tr" if text in ("çantalar", "şişeler", "kutular") else "en"
    service.translate = lambda text: {"çantalar": "The bags.", "şişeler": "Bottles.", "kutular": "Boxes."}[text]
    return service


def detection(label, left=0, score=.9):
    return {"label": label, "model_query": label, "confidence": score,
            "box": {"xmin": left, "ymin": 0, "xmax": left + 10, "ymax": 10}}


class InventoryDetector(BaseDetector):
    name = response_model = "OWL-ViT"

    def __init__(self, model="owlvit", outputs=None):
        self.model_id = model
        self.response_model = "OWL-ViT" if model == "owlvit" else "grounding-dino"
        self.calls = []
        self.outputs = outputs if outputs is not None else {
            "bag": [detection("bag"), detection("bag", score=.8), detection("bag", 20)],
            "bottle": [detection("bottle", 40)],
            "box": [],
        }

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.calls.append((list(queries), threshold, text_threshold))
        return [dict(d) for query in queries for d in self.outputs.get(query, []) if d["confidence"] > threshold]

    def _infer_raw(self, image, queries, threshold):
        return self.infer_queries(image, queries, threshold)


class InventoryQueryTests(unittest.TestCase):
    def test_single_query_keeps_original_plan(self):
        plan = process_query("bag", translator())
        self.assertEqual(plan["primary_query"], "bag")
        self.assertNotIn("processed_query_items", plan)
        result = run_detection(InventoryDetector(), None, plan)
        self.assertEqual(result["inventory_summary"], {"bag": 2})
        self.assertEqual(result["raw_detection_count"], 3)
        self.assertEqual(result["total_detected_objects"], 2)

    def test_independent_translation_normalization_and_canonical_deduplication(self):
        service = translator()
        with patch.object(service, "prepare_query", wraps=service.prepare_query) as prepare:
            plan = process_query("  çantalar, şişeler, kutular, bag, bags, çantalar, , ", service)
        self.assertEqual([i["primary_query"] for i in plan["processed_query_items"]], ["bag", "bottle", "box"])
        self.assertEqual(plan["processed_query_items"][0]["translated_query"], "The bags.")
        self.assertEqual(prepare.call_count, 5)
        self.assertTrue(plan["original_query"].startswith("  çantalar"))

    def test_empty_parts_and_duplicate_queries(self):
        for text in ("bag, bottle", "bag, bag, bottle", " , bag, , bottle, "):
            plan = process_query(text, translator())
            self.assertEqual([i["primary_query"] for i in plan["processed_query_items"]], ["bag", "bottle"])
        for text in (", ,", "  ,", "..."):
            with self.assertRaises(TranslationServiceError):
                process_query(text, translator())

    def test_nms_count_and_model_strategies(self):
        plan = process_query("bag, bottle", translator())
        for model in ("owlvit", "grounding-dino"):
            detector = InventoryDetector(model)
            result = run_detection(detector, None, plan)
            self.assertEqual(result["inventory_summary"], {"bag": 2, "bottle": 1})
            self.assertEqual(result["total_detected_objects"], 3)
            self.assertEqual(result["raw_detection_count"], 4)
            self.assertEqual(result["filtered_detection_count"], len(result["detections"]))
            self.assertTrue(all(d["canonical_query"] in ("bag", "bottle") for d in result["detections"]))
            self.assertEqual(len(detector.calls), 1 if model == "owlvit" else 2)
            self.assertFalse(result["fallback_triggered"])
            self.assertEqual(result["adaptive_thresholds_by_query"], {"bag": ADAPTIVE_THRESHOLDS[model].thresholds[0],
                                                                       "bottle": ADAPTIVE_THRESHOLDS[model].thresholds[0]})

    def test_per_query_adaptive_selection_does_not_stop_on_other_query_success(self):
        detector = InventoryDetector(outputs={"bag": [detection("bag", score=.1)], "bottle": [detection("bottle", score=.04)]})
        result = run_detection(detector, None, process_query("bag, bottle", translator()))
        self.assertEqual(result["adaptive_thresholds_by_query"], {"bag": .05, "bottle": .03})
        self.assertNotIn("adaptive_threshold_used", result)
        self.assertEqual([call[1] for call in detector.calls], [.05, .03])
        items = result["processed_query_items"]
        self.assertEqual(len(items[0]["threshold_attempts"]), 1)
        self.assertEqual(len(items[1]["threshold_attempts"]), 2)
        self.assertEqual(result["inventory_summary"], {"bag": 1, "bottle": 1})

    def test_fallback_only_after_own_primary_thresholds_and_cache_is_request_local(self):
        detector = InventoryDetector(outputs={"bottle": [detection("bottle")], "handbag": [detection("handbag")]})
        plan = process_query("bag, bottle", translator())
        for _ in range(2):
            detector.calls.clear()
            result = run_detection(detector, None, plan)
            self.assertEqual([call[1] for call in detector.calls], [.05, .03, .02, .01, .05])
            self.assertEqual(detector.calls[-1][0], ["handbag", "backpack", "tote bag"])
            self.assertEqual(result["inventory_summary"], {"bag": 1, "bottle": 1})
            self.assertTrue(result["processed_query_items"][0]["fallback_triggered"])
            self.assertFalse(result["processed_query_items"][1]["fallback_triggered"])
            found = next(d for d in result["detections"] if d["canonical_query"] == "bag")
            self.assertEqual(found["model_query"], "handbag")

    def test_zero_counts_and_deduplicated_single_item(self):
        result = run_detection(InventoryDetector(), None, process_query("bag, bag,", translator()))
        self.assertEqual(result["inventory_summary"], {"bag": 2})
        self.assertTrue(all(d["label"] == "bag" for d in result["detections"]))
        result = run_detection(InventoryDetector(), None, process_query("bottle, box", translator()))
        self.assertEqual(result["inventory_summary"], {"bottle": 1, "box": 0})

    def test_all_routes_and_compare_model_counts_without_extra_image_inference(self):
        services = {"owlvit": InventoryDetector(), "grounding-dino": InventoryDetector("grounding-dino", {"bag": [detection("bag")]})}
        registry = DetectorRegistry({key: lambda service=service: service for key, service in services.items()})
        with patch.object(main, "TranslationService", return_value=translator()), \
                patch.object(main, "DetectorRegistry", return_value=registry), TestClient(main.app) as client:
            with Image.new("RGB", (80, 40)) as image, BytesIO() as buffer:
                image.save(buffer, format="PNG")
                content = buffer.getvalue()
            results = {}
            for model, detector in services.items():
                detector.calls.clear()
                response = client.post("/detect", data={"query": "çantalar, şişeler", "model": model, "include_image": "true"},
                                       files={"image": ("test.png", content, "image/png")})
                self.assertEqual(response.status_code, 200, response.text)
                body = results[model] = response.json()
                self.assertEqual(body["original_query"], "çantalar, şişeler")
                self.assertEqual(body["processed_query_items"][1]["primary_query"], "bottle")
                with Image.open(BytesIO(b64decode(body["annotated_image"]["data_base64"]))) as image:
                    self.assertEqual(image.format, "JPEG")
                for endpoint in ("/detect-image", "/detect-raw-image"):
                    response = client.post(endpoint, data={"query": "bag, bottle", "model": model},
                                           files={"image": ("test.png", content, "image/png")})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("image/jpeg", response.headers["content-type"])
            self.assertEqual(results["owlvit"]["inventory_summary"], {"bag": 2, "bottle": 1})
            self.assertEqual(results["grounding-dino"]["inventory_summary"], {"bag": 1, "bottle": 0})
            response = client.post("/detect", data={"query": ", ,"}, files={"image": ("test.png", content, "image/png")})
            self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
