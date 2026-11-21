"""Hassasiyet seviyeleri: varsayılan kalibre edilmiş politikadır; diğerleri tek sabit eşik."""

from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import config, main
from backend.app.models.base_detector import BaseDetector, DetectorError
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.services import sensitivity


class RecordingDetector(BaseDetector):
    model_id = "grounding-dino"
    name = response_model = "fake"

    def __init__(self):
        self.thresholds = []

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.thresholds.append(threshold)
        return []

    def _infer_raw(self, image, queries, threshold):
        return self.infer_queries(image, queries, threshold)


def translator():
    service = MagicMock()
    service.prepare_query.return_value = {"original_query": "kedi", "detected_language": "tr",
                                          "translated_query": "cat", "translation_source": "lexicon",
                                          "primary_query": "cat"}
    return service


class SensitivityPolicyTests(unittest.TestCase):
    def test_balanced_is_the_calibrated_default(self):
        detector = RecordingDetector()
        self.assertIs(sensitivity.detection_policy(detector, "balanced"), config.ADAPTIVE_THRESHOLDS["grounding-dino"])
        self.assertIs(sensitivity.exemplar_settings("balanced"), config.EXEMPLAR_SEARCH)

    def test_levels_are_ordered_for_every_production_model(self):
        # Sıkı > dengeli > geniş; aksi halde arayüzdeki adlar yanıltıcı olur.
        for key, levels in config.SENSITIVITY_THRESHOLDS.items():
            balanced = config.ADAPTIVE_THRESHOLDS[key].thresholds[0]
            self.assertGreater(levels["strict"], balanced, key)
            self.assertLess(levels["loose"], balanced, key)
        self.assertGreater(config.EXEMPLAR_SENSITIVITY["strict"], config.EXEMPLAR_SEARCH.similarity_threshold)
        self.assertLess(config.EXEMPLAR_SENSITIVITY["loose"], config.EXEMPLAR_SEARCH.similarity_threshold)

    def test_other_levels_use_single_fixed_threshold(self):
        policy = sensitivity.detection_policy(RecordingDetector(), "loose")
        self.assertEqual(policy.thresholds, (config.SENSITIVITY_THRESHOLDS["grounding-dino"]["loose"],))
        self.assertFalse(policy.allow_lowering)
        self.assertEqual(sensitivity.exemplar_settings("strict").similarity_threshold, config.EXEMPLAR_SENSITIVITY["strict"])

    def test_unknown_level_is_rejected(self):
        self.assertEqual(sensitivity.validate(None), "balanced")
        self.assertEqual(sensitivity.validate(" Strict "), "strict")
        with self.assertRaises(DetectorError) as error:
            sensitivity.validate("max")
        self.assertEqual(error.exception.status_code, 422)


class SensitivityEndpointTests(unittest.TestCase):
    def post(self, **extra):
        detector = RecordingDetector()
        registry = DetectorRegistry({"grounding-dino": lambda: detector})
        buffer = BytesIO()
        Image.new("RGB", (16, 16), "white").save(buffer, format="PNG")
        with patch.object(main, "TranslationService", return_value=translator()), \
                patch.object(main, "DetectorRegistry", return_value=registry), TestClient(main.app) as client:
            response = client.post("/detect", data={"query": "kedi", "model": "grounding-dino", **extra},
                                   files={"image": ("t.png", buffer.getvalue(), "image/png")})
        return response, detector

    def test_endpoint_uses_selected_level(self):
        response, detector = self.post(sensitivity="strict")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(detector.thresholds, [config.SENSITIVITY_THRESHOLDS["grounding-dino"]["strict"]])
        self.assertEqual(response.json()["sensitivity"], "strict")

    def test_endpoint_default_is_balanced(self):
        response, detector = self.post()
        self.assertEqual(detector.thresholds[0], config.ADAPTIVE_THRESHOLDS["grounding-dino"].thresholds[0])
        self.assertEqual(response.json()["sensitivity"], "balanced")

    def test_invalid_level_returns_422_without_inference(self):
        response, detector = self.post(sensitivity="max")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(detector.thresholds, [])


if __name__ == "__main__":
    unittest.main()
