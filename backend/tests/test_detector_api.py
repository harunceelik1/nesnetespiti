from io import BytesIO
from base64 import b64decode
import unittest
from unittest.mock import MagicMock, patch
from backend.tests import legacy_adaptive


def setUpModule():
    # Eski eşik düşürme/yedek davranışı ayar olarak sınanır.
    legacy_adaptive.start()


def tearDownModule():
    legacy_adaptive.stop()

try:
    from fastapi.testclient import TestClient
    from PIL import Image
    from backend.app.main import app
    from backend.app.models.base_detector import BaseDetector
    from backend.app.services.query_processor import process_query
    from backend.app.models.detector_registry import DetectorRegistry
except ImportError:
    TestClient = None


if TestClient is not None:
    class FakeDetector(BaseDetector):
        def __init__(self, translation, model_id):
            self.model_id = model_id
            self.name = DetectorRegistry.NAMES[model_id]
            self.response_model = "OWL-ViT" if model_id == "owlvit" else model_id
            self.calls = []

        def _infer_raw(self, image, queries, threshold):
            self.calls.append((queries, threshold))
            return [{
                "label": queries[0], "model_query": "bag",
                "confidence": 0.82, "box": {"xmin": 2.0, "ymin": 2.0, "xmax": 20.0, "ymax": 20.0},
            }]


@unittest.skipIf(TestClient is None, "Backend sanal ortamını kullanın.")
class DetectorApiTests(unittest.TestCase):
    def setUp(self):
        self.translation = MagicMock()
        self.translation.prepare_query.side_effect = lambda query: {
            "original_query": query, "primary_query": "bag",
            "detected_language": "en", "translated_query": None,
        }
        self.owl = FakeDetector(self.translation, "owlvit")
        self.dino = FakeDetector(self.translation, "grounding-dino")
        self.yolo = FakeDetector(self.translation, "yolo-world")
        self.owl_factory = MagicMock(return_value=self.owl)
        self.dino_factory = MagicMock(return_value=self.dino)
        self.yolo_factory = MagicMock(return_value=self.yolo)
        self.registry = DetectorRegistry({
            "owlvit": self.owl_factory, "grounding-dino": self.dino_factory,
            "yolo-world": self.yolo_factory,
        })
        output = BytesIO()
        with Image.new("RGB", (32, 32), "white") as image:
            image.save(output, format="PNG")
        self.png = output.getvalue()

    def client(self):
        self.enterContext(patch("backend.app.main.TranslationService", return_value=self.translation))
        self.enterContext(patch("backend.app.main.DetectorRegistry", return_value=self.registry))
        # ASGI test client TCP sunucusu başlatmaz; gerçek model yüklenmez.
        return self.enterContext(TestClient(app))

    def post(self, client, path="/detect", model=None, include_image=False):
        data = {"query": "bag", "threshold": "0.2"}
        if include_image:
            data["include_image"] = "true"
        if model is not None:
            data["model"] = model
        return client.post(path, data=data, files={"image": ("test.png", self.png, "image/png")})

    def test_models_reports_loaded_models_without_inference(self):
        client = self.client()
        response = client.get("/models")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"models": [
            {"id": "owlvit", "name": "OWL-ViT", "available": True},
            {"id": "grounding-dino", "name": "Grounding DINO", "available": True},
            {"id": "yolo-world", "name": "YOLO-World", "available": True},
        ]})
        self.assertEqual(self.owl.calls, [])
        self.assertEqual(self.dino.calls, [])
        self.assertEqual(self.yolo.calls, [])

    def test_default_and_explicit_owl_preserve_old_fields(self):
        client = self.client()
        for model in (None, "owlvit"):
            with self.subTest(model=model):
                response = self.post(client, model=model)
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["model"], "OWL-ViT")
                self.assertEqual(body["model_id"], "owlvit")
                self.assertEqual(body["original_query"], "bag")
                self.assertEqual(body["primary_query"], "bag")
                self.assertEqual(body["raw_detection_count"], 1)
                self.assertEqual(body["filtered_detection_count"], 1)
                self.assertEqual(body["device"], "cpu")
                self.assertIsInstance(body["inference_time_ms"], float)
                self.assertEqual(body["adaptive_threshold_used"], 0.05)
                self.assertEqual(body["threshold_selection_reason"], "first_valid_result")
                self.assertEqual(len(body["threshold_attempts"]), 1)
                self.assertNotIn("annotated_image", body)
        self.assertEqual(len(self.owl.calls), 2)
        self.assertEqual(self.dino.calls, [])
        self.owl_factory.assert_called_once()
        self.dino_factory.assert_called_once()

    def test_grounding_dino_only_runs_selected_model(self):
        client = self.client()
        response = self.post(client, model="grounding-dino")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "grounding-dino")
        self.assertEqual(len(self.dino.calls), 1)
        self.assertEqual(self.owl.calls, [])
        self.assertEqual(self.yolo.calls, [])

    def test_yolo_world_only_runs_selected_model(self):
        client = self.client()
        response = self.post(client, model="yolo-world")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["model"], "yolo-world")
        self.assertEqual(body["model_id"], "yolo-world")
        self.assertEqual(body["inventory_summary"], {"bag": 1})
        # YOLO-World kendi adaptive eşik listesiyle başlar.
        self.assertEqual(self.yolo.calls[0][1], 0.25)
        self.assertEqual(self.owl.calls, [])
        self.assertEqual(self.dino.calls, [])

    def test_combined_response_contains_jpeg_and_metadata_from_single_model_run(self):
        client = self.client()
        from backend.app import main
        for model, detector in [("owlvit", self.owl), ("grounding-dino", self.dino), ("yolo-world", self.yolo)]:
            with self.subTest(model=model), patch.object(main, "run_detection", wraps=main.run_detection) as run:
                detector.calls.clear()
                body = self.post(client, model=model, include_image=True).json()
                run.assert_called_once()
                self.assertEqual(len(detector.calls), 1)
                self.assertEqual(body["model_id"], model)
                self.assertIn("adaptive_threshold_used", body)
                self.assertIn("threshold_attempts", body)
                self.assertIn("threshold_selection_reason", body)
                self.assertEqual(body["annotated_image"]["media_type"], "image/jpeg")
                with Image.open(BytesIO(b64decode(body["annotated_image"]["data_base64"]))) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, (32, 32))

    def test_jpeg_endpoints_use_selected_model(self):
        client = self.client()
        for model in ("owlvit", "grounding-dino", "yolo-world"):
            with self.subTest(model=model):
                response = self.post(client, path="/detect-image", model=model)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/jpeg")
                self.assertEqual(response.headers["x-model"], model)
                self.assertGreaterEqual(float(response.headers["x-inference-time-ms"]), 0)
                with Image.open(BytesIO(response.content)) as image:
                    self.assertEqual(image.format, "JPEG")

    def test_invalid_model_returns_400_without_running_a_model(self):
        client = self.client()
        for path in ("/detect", "/detect-image"):
            response = self.post(client, path=path, model="unknown")
            self.assertEqual(response.status_code, 400)
            self.assertIn("Geçersiz model", response.json()["detail"])
        self.assertEqual(self.owl.calls, [])
        self.assertEqual(self.dino.calls, [])
        self.assertEqual(self.yolo.calls, [])

    def test_adaptive_json_and_jpeg_use_same_selected_threshold(self):
        client = self.client()
        detection = self.owl._infer_raw(None, ["bag"], 0.03)
        self.owl.calls.clear()
        def infer(image, queries, threshold):
            self.owl.calls.append((queries, threshold))
            return detection if threshold == 0.03 else []
        with patch.object(self.owl, "_infer_raw", side_effect=infer):
            body = self.post(client).json()
            self.assertEqual(body["adaptive_threshold_used"], 0.03)
            self.assertEqual(body["filtered_detection_count"], 1)
            self.assertEqual([a["threshold"] for a in body["threshold_attempts"]], [0.05, 0.03])
            json_calls = list(self.owl.calls)
            self.owl.calls.clear()
            response = self.post(client, path="/detect-image")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.owl.calls, json_calls)

    def test_failed_dino_load_does_not_break_app_or_owl(self):
        def fail():
            raise RuntimeError("internal download failure")
        with self.assertLogs("backend.app.models.detector_registry", level="ERROR"):
            self.registry = DetectorRegistry({
                "owlvit": self.owl_factory, "grounding-dino": fail,
                "yolo-world": self.yolo_factory,
            })
        client = self.client()
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        self.assertFalse(client.get("/models").json()["models"][1]["available"])
        response = self.post(client, model="grounding-dino")
        self.assertEqual(response.status_code, 503)
        self.assertIn("yüklenemedi", response.json()["detail"])
        self.assertNotIn("internal download failure", response.text)
        self.assertEqual(self.post(client, model="owlvit").status_code, 200)
        self.assertEqual(self.post(client, model="yolo-world").status_code, 200)

    def test_failed_yolo_world_load_keeps_other_models_available(self):
        def fail():
            raise ImportError("No module named 'ultralytics'")
        with self.assertLogs("backend.app.models.detector_registry", level="ERROR"):
            self.registry = DetectorRegistry({
                "owlvit": self.owl_factory, "grounding-dino": self.dino_factory, "yolo-world": fail,
            })
        client = self.client()
        availability = {m["id"]: m["available"] for m in client.get("/models").json()["models"]}
        self.assertEqual(availability, {"owlvit": True, "grounding-dino": True, "yolo-world": False})
        response = self.post(client, model="yolo-world")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("ultralytics", response.text)
        self.assertEqual(self.post(client, model="grounding-dino").status_code, 200)

    def test_raw_debug_endpoint_defaults_to_owl(self):
        client = self.client()
        response = self.post(client, path="/detect-raw-image")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(len(self.owl.calls), 1)
        self.assertEqual(self.owl.calls[0][1], 0.2)
        self.assertEqual(self.dino.calls, [])

    def test_inference_time_uses_perf_counter(self):
        with patch("backend.app.models.base_detector.perf_counter", side_effect=[10.0, 10.85]):
            result = self.owl.detect_result(None, process_query("bag", self.translation), 0.2)
        self.assertAlmostEqual(result["inference_time_ms"], 850)


if __name__ == "__main__":
    unittest.main()
