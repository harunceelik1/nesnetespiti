"""ASGI route -> gerçek orchestrator/detector -> gerçek HF post-process regression.

TCP sunucusu açılmaz. Ağırlıkların yerini sabit logits/boxes alır; confidence
threshold, query planı, NMS, JSON serileştirme ve JPEG çizimi gerçek kodu kullanır.
"""

from io import BytesIO
from base64 import b64decode
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
from fastapi.testclient import TestClient
from PIL import Image
from transformers import OwlViTImageProcessor, OwlViTProcessor

from backend.app import main
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.models.owlvit_service import OwlViTService
from backend.app.services.inference_orchestrator import run_detection
from backend.app.services.translation_service import TranslationService


# Bu dosya sorgu aktarımını birebir sınar; karşıt sorgular (test_contrastive.py) kapatılır.
from backend.app.config import ContrastiveQuerySettings as _ContrastiveSettings
from backend.tests import legacy_adaptive
_contrastive_patch = patch("backend.app.config.CONTRASTIVE_QUERIES", _ContrastiveSettings(enabled=False))


def setUpModule():
    legacy_adaptive.start()
    _contrastive_patch.start()


def tearDownModule():
    legacy_adaptive.stop()
    _contrastive_patch.stop()



class RecordingProcessor:
    def __init__(self):
        self.calls = []
        self.queries = []
        self.real = OwlViTProcessor.__new__(OwlViTProcessor)
        self.real.image_processor = OwlViTImageProcessor()

    def __call__(self, *, text, images, return_tensors):
        self.queries = text[0]
        return {}

    def post_process_grounded_object_detection(self, **kwargs):
        self.calls.append((list(self.queries), kwargs["threshold"]))
        return self.real.post_process_grounded_object_detection(**kwargs)


class AdaptiveRuntimeWiringTests(unittest.TestCase):
    def setUp(self):
        self.primary_scores = [0.04, 0.045]
        # Fallback erken çalışırsa güçlü ama yanlış sonucu seçerek testi bozar.
        self.fallback_scores = [0.9, 0.9]
        self.processor = RecordingProcessor()
        service = OwlViTService.__new__(OwlViTService)
        service.processor = self.processor
        def model(**inputs):
            scores = self.primary_scores if self.processor.queries == ["bag"] else self.fallback_scores
            logits = torch.full((1, 2, len(self.processor.queries)), -100.0)
            logits[0, :, 0] = torch.logit(torch.tensor(scores))
            return SimpleNamespace(logits=logits, pred_boxes=torch.tensor([
                [[0.2, 0.3, 0.2, 0.3], [0.8, 0.6, 0.2, 0.3]],
            ]))
        service.model = model
        registry = DetectorRegistry({"owlvit": lambda: service})
        translation = TranslationService.__new__(TranslationService)
        translation.detect_language = lambda query: "en"
        self.enterContext(patch.object(main, "TranslationService", return_value=translation))
        self.enterContext(patch.object(main, "DetectorRegistry", return_value=registry))
        self.orchestrator = self.enterContext(patch.object(main, "run_detection", wraps=run_detection))
        self.annotation = self.enterContext(patch.object(main, "annotate_image", wraps=main.annotate_image))
        self.client = self.enterContext(TestClient(main.app))
        with Image.new("RGB", (100, 100), "white") as image, BytesIO() as output:
            image.save(output, format="PNG")
            self.image = output.getvalue()

    def post(self, endpoint="/detect", threshold=None, include_image=False):
        data = {"query": "bag", "model": "owlvit"}
        if include_image:
            data["include_image"] = "true"
        if threshold is not None:
            data["threshold"] = str(threshold)
        response = self.client.post(endpoint, data=data, files={"image": ("two-bags.png", self.image, "image/png")})
        self.assertEqual(response.status_code, 200)
        return response

    def test_real_route_uses_adaptive_threshold_before_any_fallback(self):
        for threshold in (None, 0.2, 0.99, 0.01):
            with self.subTest(legacy_threshold=threshold):
                self.processor.calls.clear()
                self.orchestrator.reset_mock()
                body = self.post(threshold=threshold).json()
                self.orchestrator.assert_called_once()
                self.assertEqual(self.processor.calls, [(["bag"], 0.05), (["bag"], 0.03)])
                self.assertEqual(body["adaptive_threshold_used"], 0.03)
                self.assertEqual(body["threshold_selection_reason"], "first_valid_result")
                self.assertEqual(body["raw_detection_count"], 2)
                self.assertEqual(body["filtered_detection_count"], 2)
                self.assertEqual(body["processed_queries"], ["bag"])
                self.assertFalse(body["fallback_triggered"])
                self.assertEqual(body["fallback_queries_used"], [])
                self.assertEqual([(a["threshold"], a["raw_detection_count"], a["filtered_detection_count"])
                                  for a in body["threshold_attempts"]], [(0.05, 0, 0), (0.03, 2, 2)])

    def test_json_and_jpeg_use_same_orchestrator_decision_and_detections(self):
        body = self.post().json()
        json_calls = list(self.processor.calls)
        self.processor.calls.clear()
        self.orchestrator.reset_mock()
        response = self.post("/detect-image")
        self.orchestrator.assert_called_once()
        self.assertEqual(self.processor.calls, json_calls)
        self.assertEqual(self.annotation.call_args.args[1], body["detections"])
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(float(response.headers["x-adaptive-threshold-used"]), body["adaptive_threshold_used"])
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.format, "JPEG")

    def test_fallback_waits_until_every_primary_threshold_is_empty(self):
        self.primary_scores = [0.001, 0.002]
        body = self.post().json()
        self.assertEqual(self.processor.calls, [
            (["bag"], 0.05), (["bag"], 0.03), (["bag"], 0.02), (["bag"], 0.01),
            (["handbag", "backpack", "tote bag"], 0.05),
        ])
        self.assertTrue(body["fallback_triggered"])
        self.assertEqual(body["primary_query"], "bag")
        self.assertEqual(body["processed_queries"], ["bag", "handbag", "backpack", "tote bag"])
        self.assertEqual(len(body["threshold_attempts"]), 5)

    def test_first_primary_threshold_stops_immediately(self):
        self.primary_scores = [0.2, 0.3]
        body = self.post().json()
        self.assertEqual(self.processor.calls, [(["bag"], 0.05)])
        self.assertFalse(body["fallback_triggered"])

    def test_combined_response_without_threshold_reuses_exact_detection_list(self):
        body = self.post(include_image=True).json()
        self.orchestrator.assert_called_once()
        self.assertEqual(self.processor.calls, [(["bag"], 0.05), (["bag"], 0.03)])
        self.assertEqual(body["adaptive_threshold_used"], 0.03)
        self.assertEqual(body["filtered_detection_count"], 2)
        self.assertEqual(self.annotation.call_args.args[1], body["detections"])
        with Image.open(BytesIO(b64decode(body["annotated_image"]["data_base64"]))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (100, 100))

    def test_empty_response_still_has_adaptive_metadata(self):
        self.primary_scores = self.fallback_scores = [0.001, 0.002]
        body = self.post().json()
        self.assertEqual(body["detections"], [])
        self.assertEqual(body["adaptive_threshold_used"], 0.01)
        self.assertEqual(body["threshold_selection_reason"], "no_detections")
        self.assertEqual(len(body["threshold_attempts"]), 8)


if __name__ == "__main__":
    unittest.main()
