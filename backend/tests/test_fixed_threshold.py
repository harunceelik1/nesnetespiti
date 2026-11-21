"""Üretim varsayılanı: eşik düşürülmez, eş anlamlı yedek çalışmaz → bulunamazsa boş döner."""

import unittest

from backend.app import config
from backend.app.models.base_detector import BaseDetector
from backend.app.services.inference_orchestrator import run_detection


def det(score, label="medicine box"):
    return {"label": label, "model_query": label, "confidence": score,
            "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}}


class Fake(BaseDetector):
    model_id, name, response_model = "grounding-dino", "Fake", "fake"

    def __init__(self, by_threshold):
        self.by_threshold, self.calls = by_threshold, []

    def _infer_raw(self, image, queries, threshold):
        return []

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.calls.append((list(queries), threshold))
        return self.by_threshold.get(threshold, [])


PLAN = {"original_query": "çanta", "detected_language": "tr", "translated_query": "bag",
        "primary_query": "bag", "fallback_queries": ["handbag", "backpack"]}


class FixedThresholdDefaultsTests(unittest.TestCase):
    def test_production_defaults_are_conservative(self):
        self.assertFalse(config.SYNONYM_FALLBACK_ENABLED)
        self.assertTrue(all(not policy.allow_lowering for policy in config.ADAPTIVE_THRESHOLDS.values()))

    def test_absent_object_is_not_searched_at_lower_thresholds_or_synonyms(self):
        # Eski akış 0.25'te zayıf bir kutu ve "handbag" yedeğiyle uydurma yapardı.
        detector = Fake({0.25: [det(0.26, "bag")]})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["threshold_selection_reason"], "no_detections")
        self.assertEqual(detector.calls, [(["bag"], config.ADAPTIVE_THRESHOLDS["grounding-dino"].thresholds[0])])
        self.assertFalse(result["fallback_triggered"])

    def test_confident_detection_is_kept(self):
        first = config.ADAPTIVE_THRESHOLDS["grounding-dino"].thresholds[0]
        detector = Fake({first: [det(0.8, "bag")]})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(len(result["detections"]), 1)
        self.assertEqual(result["adaptive_threshold_used"], first)


if __name__ == "__main__":
    unittest.main()
