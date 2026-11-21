"""YOLO-World servis sözleşmesi; Ultralytics ağırlığı indirilmez, sahte model kullanılır."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from backend.tests import legacy_adaptive


def setUpModule():
    # Eski eşik düşürme/yedek davranışı ayar olarak sınanır.
    legacy_adaptive.start()


def tearDownModule():
    legacy_adaptive.stop()

try:
    import torch
    from PIL import Image
    from backend.app.config import ADAPTIVE_THRESHOLDS, YoloWorldSettings
    from backend.app.models.base_detector import DetectorError
    from backend.app.models.yoloworld_service import CACHE_DIR, YoloWorldService
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
except ImportError:
    YoloWorldService = None


class FakeWorldModel:
    """Ultralytics WorldModel'in set_classes/names yüzeyi."""

    def __init__(self):
        self.set_calls = []
        self.names = None

    def set_classes(self, names, cache_clip_model=False):
        self.set_calls.append((list(names), cache_clip_model))


class FakeYoloWorld:
    """Ultralytics YOLOWorld: .model, .predictor ve .predict(...)."""

    def __init__(self, weights, outputs=None):
        self.weights = weights
        self.model = FakeWorldModel()
        self.predictor = "kurulu"
        self.predict_calls = []
        # outputs: threshold -> [(xyxy, score, class_index), ...]
        self.outputs = outputs or {}

    def predict(self, **kwargs):
        self.predict_calls.append(kwargs)
        rows = [row for row in self.outputs.get("rows", []) if row[1] >= kwargs["conf"]]
        boxes = SimpleNamespace(
            xyxy=torch.tensor([row[0] for row in rows], dtype=torch.float32).reshape(-1, 4),
            conf=torch.tensor([row[1] for row in rows], dtype=torch.float32),
            cls=torch.tensor([row[2] for row in rows], dtype=torch.float32),
        )
        return [SimpleNamespace(boxes=boxes)]


@unittest.skipIf(YoloWorldService is None, "Backend sanal ortamını kullanın.")
class YoloWorldServiceTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", (100, 80), "white")
        self.translation = MagicMock()
        self.translation.prepare_query.side_effect = lambda query: {
            "original_query": query, "primary_query": query,
            "detected_language": "en", "translated_query": None,
        }
        self.created = []

    def tearDown(self):
        self.image.close()

    def make_service(self, rows=None, cuda=False):
        def factory(weights):
            model = FakeYoloWorld(weights, {"rows": rows or []})
            self.created.append(model)
            return model
        with patch("backend.app.models.yoloworld_service.torch.cuda.is_available", return_value=cuda):
            return YoloWorldService(YoloWorldSettings(), model_factory=factory)

    def test_contract_labels_boxes_and_threshold(self):
        service = self.make_service([([10, 20, 70, 75], 0.62, 0)])
        result = service.detect_result(self.image, process_query("wallet", self.translation), threshold=0.25)
        self.assertEqual(result["model"], "yolo-world")
        self.assertEqual(result["model_id"], "yolo-world")
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(len(result["detections"]), 1)
        detection = result["detections"][0]
        self.assertEqual(detection["model_query"], "wallet")
        self.assertAlmostEqual(detection["confidence"], 0.62, places=5)
        self.assertEqual(detection["box"], {"xmin": 10.0, "ymin": 20.0, "xmax": 70.0, "ymax": 75.0})
        call = self.created[0].predict_calls[-1]
        self.assertEqual(call["conf"], 0.25)
        self.assertEqual(call["iou"], 0.70)
        self.assertEqual(call["device"], "cpu")
        self.assertIs(call["source"], self.image)
        self.assertFalse(call["verbose"])

    def test_weights_live_in_project_cache_and_model_loads_once(self):
        service = self.make_service()
        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.created[0].weights, str(CACHE_DIR / "yolov8s-worldv2.pt"))
        self.assertEqual(service.weights_path.parent.name, "yolo-world")
        service.detect_result(self.image, process_query("bag", self.translation), 0.2)
        service.detect_result(self.image, process_query("bag", self.translation), 0.1)
        self.assertEqual(len(self.created), 1)

    def test_text_embeddings_are_cached_per_class_list(self):
        service = self.make_service()
        world = self.created[0].model
        # Başlangıçta CLIP ısındırma sınıfı ayarlanır.
        self.assertEqual(world.set_calls, [(["object"], True)])
        service.infer_queries(self.image, ["wallet"], 0.25)
        service.infer_queries(self.image, ["wallet"], 0.15)
        service.infer_queries(self.image, ["earbuds case", "headphones"], 0.15)
        self.assertEqual(world.set_calls, [
            (["object"], True), (["wallet"], True), (["earbuds case", "headphones"], True),
        ])
        self.assertEqual(world.names, ["earbuds case", "headphones"])
        # Sınıf değişince predictor yeni adlarla yeniden kurulur.
        self.assertIsNone(self.created[0].predictor)

    def test_multiple_classes_map_back_to_sent_queries(self):
        service = self.make_service([([1, 1, 20, 20], 0.5, 1), ([30, 30, 60, 60], 0.4, 0)])
        detections = service.infer_queries(self.image, ["headphones", "earbuds case"], 0.1)
        self.assertEqual([d["label"] for d in detections], ["earbuds case", "headphones"])

    def test_empty_query_and_model_failure_are_explained(self):
        service = self.make_service()
        with self.assertRaises(DetectorError) as empty:
            service.infer_queries(self.image, ["  "], 0.25)
        self.assertEqual(empty.exception.status_code, 422)
        self.created[0].predict = MagicMock(side_effect=RuntimeError("internal"))
        with self.assertLogs("backend.app.models.yoloworld_service", level="ERROR"):
            with self.assertRaises(DetectorError) as failure:
                service.infer_queries(self.image, ["bag"], 0.25)
        self.assertEqual(failure.exception.status_code, 503)
        self.assertNotIn("internal", str(failure.exception))

    def test_cuda_selection_and_synchronize(self):
        service = self.make_service(cuda=True)
        with patch("backend.app.models.yoloworld_service.torch.cuda.synchronize") as synchronize:
            service.infer_queries(self.image, ["bag"], 0.25)
        self.assertEqual(service.device, "cuda")
        self.assertEqual(self.created[0].predict_calls[-1]["device"], "cuda")
        self.assertEqual(synchronize.call_count, 2)

    def test_adaptive_policy_lowers_threshold_until_a_result(self):
        service = self.make_service([([10, 10, 50, 50], 0.14, 0)])
        result = run_detection(service, self.image, process_query("wallet", self.translation))
        self.assertEqual([a["threshold"] for a in result["threshold_attempts"]], [0.25, 0.15, 0.10])
        self.assertEqual(result["adaptive_threshold_used"], 0.10)
        self.assertEqual(result["inventory_summary"], {"wallet": 1})
        self.assertEqual(ADAPTIVE_THRESHOLDS["yolo-world"].thresholds, (0.25, 0.15, 0.10, 0.05))

    def test_settings_are_validated(self):
        with self.assertRaises(ValueError):
            YoloWorldSettings(weights="model.onnx")
        with self.assertRaises(ValueError):
            YoloWorldSettings(model_nms_iou=0)


if __name__ == "__main__":
    unittest.main()
