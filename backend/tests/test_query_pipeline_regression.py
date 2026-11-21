"""Aynı görüntü + bag/çanta: gerçek detector processor sınırına gelen prompt'u izle."""
from io import BytesIO
from threading import Lock
import unittest
from unittest.mock import MagicMock, patch
from backend.tests import legacy_adaptive

try:
    import torch
    from fastapi.testclient import TestClient
    from PIL import Image
    from backend.app.main import app, prepare_detection
    from backend.app.config import ADAPTIVE_THRESHOLDS, GROUNDING_DINO, ContrastiveQuerySettings
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.models.owlvit_service import OwlViTService
    from backend.app.models.grounding_dino_service import GroundingDinoService
    from backend.app.services.translation_service import TranslationService
except ImportError:
    TestClient = None


# Bu dosya Marian model çeviri yolunu sınar; Türkçe nesne sözlüğü devre dışı bırakılır.
_lexicon_patch = patch("backend.app.services.object_lexicon.lookup", return_value=None)


_contrastive_patch = patch("backend.app.config.CONTRASTIVE_QUERIES", ContrastiveQuerySettings(enabled=False))


def setUpModule():
    legacy_adaptive.start()
    _lexicon_patch.start()
    _contrastive_patch.start()


def tearDownModule():
    legacy_adaptive.stop()
    _lexicon_patch.stop()
    _contrastive_patch.stop()


@unittest.skipIf(TestClient is None, "Backend sanal ortamını kullanın.")
class QueryPipelineRegressionTests(unittest.TestCase):
    def setUp(self):
        # prepare_query ve query processor gerçektir; modelin gözlenen "The bag."
        # çevirisini üretmek için yalnızca dil tespiti/çeviri ağırlıkları taklit edilir.
        self.translation = TranslationService.__new__(TranslationService)
        self.translation.detect_language = MagicMock(side_effect=lambda text: "en" if text == "bag" else "tr")
        self.translation.translate = MagicMock(return_value="The bag.")
        self.services = {}
        for model_id, cls in [("owlvit", OwlViTService), ("grounding-dino", GroundingDinoService)]:
            service = cls.__new__(cls)
            service.device = "cpu"
            service.model = MagicMock()
            service.processor = MagicMock()
            if model_id == "grounding-dino":
                service.config = GROUNDING_DINO
                service._lock = Lock()
                inputs = MagicMock()
                inputs.to.return_value = {"input_ids": torch.tensor([[1, 2]])}
                service.processor.return_value = inputs
            else:
                service.processor.return_value = {"pixel_values": torch.zeros(1)}
            self.services[model_id] = service
        self.registry = DetectorRegistry({
            model: (lambda service=service: service) for model, service in self.services.items()
        })
        self.enterContext(patch("backend.app.main.TranslationService", return_value=self.translation))
        self.enterContext(patch("backend.app.main.DetectorRegistry", return_value=self.registry))
        self.client = self.enterContext(TestClient(app))
        output = BytesIO()
        with Image.new("RGB", (32, 32), "white") as image:
            image.save(output, format="PNG")
        self.image = output.getvalue()

    @staticmethod
    def result(empty=False):
        return [{
            "boxes": torch.empty((0, 4)) if empty else torch.tensor([[2., 2., 20., 20.]]),
            "scores": torch.empty(0) if empty else torch.tensor([0.82]),
            "text_labels": [] if empty else ["bag"],
        }]

    def post(self, endpoint, model, query):
        return self.client.post(endpoint, data={"query": query, "model": model, "threshold": "0.2"},
                                files={"image": ("same.png", self.image, "image/png")})

    def test_primary_reaches_both_real_detector_processors_for_all_endpoints(self):
        for endpoint in ["/detect", "/detect-image", "/detect-raw-image"]:
            for model, service in self.services.items():
                texts = []
                for query in ["bag", "çanta"]:
                    with self.subTest(endpoint=endpoint, model=model, query=query):
                        service.processor.reset_mock()
                        service.processor.post_process_grounded_object_detection.side_effect = None
                        service.processor.post_process_grounded_object_detection.return_value = self.result()
                        response = self.post(endpoint, model, query)
                        self.assertEqual(response.status_code, 200, response.text if endpoint == "/detect" else "")
                        text = service.processor.call_args.kwargs["text"]
                        self.assertEqual(text, [["bag"]])
                        texts.append(text)
                        if endpoint == "/detect":
                            body = response.json()
                            self.assertEqual(body["original_query"], query)
                            self.assertEqual(body["primary_query"], "bag")
                            self.assertEqual(body["model_id"], model)
                            self.assertEqual(body["detected_language"], "tr" if query == "çanta" else "en")
                            self.assertEqual(body["translated_query"], "The bag." if query == "çanta" else None)
                        else:
                            self.assertEqual(response.headers["content-type"], "image/jpeg")
                self.assertEqual(texts[0], texts[1])

    def test_fallback_uses_same_english_queries_without_retranslation(self):
        for endpoint in ["/detect", "/detect-image", "/detect-raw-image"]:
            for model, service in self.services.items():
                for query in ["bag", "çanta"]:
                    with self.subTest(endpoint=endpoint, model=model, query=query):
                        service.processor.reset_mock()
                        self.translation.detect_language.reset_mock()
                        # Normal endpoint'lerde tüm primary eşikleri boş kalmadan
                        # fallback başlayamaz. Raw debug eski tek eşik akışındadır.
                        primary_attempts = 1 if endpoint == "/detect-raw-image" else len(ADAPTIVE_THRESHOLDS[model].thresholds)
                        service.processor.post_process_grounded_object_detection.side_effect = [
                            *[self.result(empty=True) for _ in range(primary_attempts)], self.result(),
                        ]
                        response = self.post(endpoint, model, query)
                        self.assertEqual(response.status_code, 200)
                        texts = [call.kwargs["text"] for call in service.processor.call_args_list]
                        self.assertEqual(texts, [[["bag"]]] * primary_attempts + [[["handbag", "backpack", "tote bag"]]])
                        self.translation.detect_language.assert_called_once()
                        if endpoint == "/detect":
                            self.assertTrue(response.json()["fallback_triggered"])

    def test_processing_happens_before_detector_selection(self):
        events = []
        prepare = self.translation.prepare_query
        get_detector = self.registry.get
        with patch.object(self.translation, "prepare_query", side_effect=lambda q: (events.append("process"), prepare(q))[1]):
            with patch.object(self.registry, "get", side_effect=lambda m: (events.append("select"), get_detector(m))[1]):
                from types import SimpleNamespace
                request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
                    translation_service=self.translation, detector_registry=self.registry,
                )))
                detector, plan = prepare_detection(request, "çanta", "grounding-dino")
        self.assertEqual(events, ["process", "select"])
        self.assertEqual(plan["primary_query"], "bag")
        self.assertIs(detector, self.services["grounding-dino"])

    def test_normalized_plural_reaches_both_detectors_and_debug_fields(self):
        examples = {"people": "person", "bags": "bag", "plants": "plant", "pillows": "pillow", "çantalar": "bag"}
        self.translation.detect_language.side_effect = lambda text: "tr" if text == "çantalar" else "en"
        self.translation.translate.return_value = "The bags."
        for endpoint in ["/detect", "/detect-image", "/detect-raw-image"]:
            for model, service in self.services.items():
                for query, expected in examples.items():
                    with self.subTest(endpoint=endpoint, model=model, query=query):
                        service.processor.reset_mock()
                        output = self.result()
                        output[0]["text_labels"] = [expected]
                        service.processor.post_process_grounded_object_detection.return_value = output
                        response = self.post(endpoint, model, query)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(service.processor.call_args.kwargs["text"], [[expected]])
                        if endpoint == "/detect":
                            body = response.json()
                            self.assertEqual(body["original_query"], query)
                            self.assertEqual(body["translated_query"], "The bags." if query == "çantalar" else None)
                            self.assertEqual(body["primary_query"], expected)
                            self.assertEqual(body["processed_queries"], [expected])
                            self.assertFalse(body["fallback_triggered"])

    def test_invalid_model_still_returns_400_before_translation(self):
        response = self.post("/detect", "invalid", "çanta")
        self.assertEqual(response.status_code, 400)
        self.translation.detect_language.assert_not_called()


if __name__ == "__main__":
    unittest.main()
