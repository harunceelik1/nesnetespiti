"""Arayüzdeki "Aranan ifade" düzeltmesi: english_query çeviriyi atlar, etiket Türkçe kalır."""

from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import main
from backend.app.models.base_detector import BaseDetector
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.services.query_processor import process_query
from backend.app.services.translation_service import TranslationServiceError


def translator():
    service = MagicMock()
    # Düzeltme verildiğinde çeviri hiç çağrılmamalı.
    service.prepare_query.side_effect = AssertionError("çeviri çağrılmamalı")
    return service


class RecordingDetector(BaseDetector):
    model_id = "grounding-dino"
    name = response_model = "fake"

    def __init__(self):
        self.queries = []

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.queries.append(list(queries))
        return [{"label": queries[0], "model_query": queries[0], "confidence": 0.9,
                 "box": {"xmin": 1, "ymin": 1, "xmax": 10, "ymax": 10}}]

    def _infer_raw(self, image, queries, threshold):
        return self.infer_queries(image, queries, threshold)


class QueryOverrideTests(unittest.TestCase):
    def test_single_override_skips_translation_and_keeps_turkish_label(self):
        plan = process_query("ilaç kutusu", translator(), english_query="  Pill Box ")
        self.assertEqual(plan["primary_query"], "pill box")
        self.assertEqual(plan["original_query"], "ilaç kutusu")
        self.assertEqual(plan["translation_source"], "user")
        self.assertEqual(plan["translated_query"], "Pill Box")

    def test_multi_override_maps_parts_in_order(self):
        plan = process_query("çikolata, sakız", translator(), english_query="chocolate bar, chewing gum")
        items = plan["processed_query_items"]
        self.assertEqual([(i["original_query"], i["primary_query"]) for i in items],
                         [("çikolata", "chocolate bar"), ("sakız", "chewing gum")])
        self.assertEqual(plan["translation_source"], "user")

    def test_part_count_mismatch_is_rejected(self):
        with self.assertRaises(TranslationServiceError) as error:
            process_query("çikolata, sakız", translator(), english_query="chocolate bar")
        self.assertEqual(error.exception.status_code, 422)

    def test_blank_override_falls_back_to_normal_translation(self):
        service = MagicMock()
        service.prepare_query.return_value = {"original_query": "kravat", "detected_language": "tr",
                                              "translated_query": "tie", "translation_source": "lexicon",
                                              "primary_query": "tie"}
        for blank in (None, "", "   "):
            self.assertEqual(process_query("kravat", service, english_query=blank)["primary_query"], "tie")

    def test_endpoint_sends_override_to_detector(self):
        detector = RecordingDetector()
        registry = DetectorRegistry({"grounding-dino": lambda: detector})
        buffer = BytesIO()
        Image.new("RGB", (16, 16), "white").save(buffer, format="PNG")
        with patch.object(main, "TranslationService", return_value=translator()), \
                patch.object(main, "DetectorRegistry", return_value=registry), TestClient(main.app) as client:
            response = client.post("/detect", data={"query": "ilaç kutusu", "english_query": "pill box",
                                                    "model": "grounding-dino"},
                                   files={"image": ("t.png", buffer.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(detector.queries[0][0], "pill box")
        self.assertEqual(body["primary_query"], "pill box")
        self.assertEqual(body["translation_source"], "user")
        self.assertEqual(body["detections"][0]["label"], "ilaç kutusu")


if __name__ == "__main__":
    unittest.main()
