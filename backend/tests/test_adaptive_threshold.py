"""Model indirmeden ortak orchestration, gerçek fallback ve NMS regression testleri."""

import unittest
import json
from unittest.mock import patch

from backend.app.config import ADAPTIVE_THRESHOLDS, GROUNDING_DINO
from backend.app.models.base_detector import BaseDetector
from backend.app.services.inference_orchestrator import run_detection
from backend.tests import legacy_adaptive


def setUpModule():
    # Eski eşik düşürme/yedek davranışı ayar olarak sınanır.
    legacy_adaptive.start()


def tearDownModule():
    legacy_adaptive.stop()


PLAN = {
    "original_query": "çanta", "detected_language": "tr", "translated_query": "bag",
    "primary_query": "bag", "fallback_queries": [],
}


def boxes(count, score):
    return [
        {"label": "bag", "model_query": "bag", "confidence": score,
         "box": {"xmin": index * 20, "ymin": 0, "xmax": index * 20 + 10, "ymax": 10}}
        for index in range(count)
    ]


class FakeDetector(BaseDetector):
    model_id = "owlvit"
    name = response_model = "OWL-ViT"

    def __init__(self, results, model_id="owlvit"):
        self.results = results
        self.calls = []
        self.model_id = model_id

    def _infer_raw(self, image, queries, threshold):
        self.calls.append((queries, threshold, None))
        return self.results.get(threshold, [])

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        self.calls.append((queries, threshold, text_threshold))
        return self.results.get(threshold, [])


class AdaptiveThresholdTests(unittest.TestCase):
    def test_empty_at_005_selects_003(self):
        detector = FakeDetector({0.03: boxes(2, 0.08)})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(result["adaptive_threshold_used"], 0.03)
        self.assertEqual([call[1] for call in detector.calls], [0.05, 0.03])
        self.assertEqual([attempt["detections"] for attempt in result["threshold_attempts"]], [0, 2])
        self.assertEqual(result["threshold_selection_reason"], "first_valid_result")
        self.assertEqual(result["original_query"], "çanta")
        self.assertEqual(result["primary_query"], "bag")
        self.assertTrue(all(call[0] == ["bag"] for call in detector.calls))

    def test_first_valid_result_stops_without_more_inference(self):
        detector = FakeDetector({0.05: boxes(2, 0.1), 0.03: boxes(11, 0.04)})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(len(detector.calls), 1)
        self.assertEqual(result["adaptive_threshold_used"], 0.05)

    def test_explosion_at_001_preserves_previous_controlled_result(self):
        # Önceki iki kutu eşiğe çok yakın olduğundan geçici adaydır; ilk makul
        # sonuç olsalardı aşağıdaki 0.01 denemesi zaten yapılmayacaktı.
        detector = FakeDetector({0.02: boxes(2, 0.022), 0.01: boxes(61, 0.012)})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(result["adaptive_threshold_used"], 0.02)
        self.assertEqual(len(result["detections"]), 2)
        self.assertEqual(result["threshold_attempts"][-1]["assessment"], "detection_explosion")
        self.assertEqual(result["threshold_selection_reason"], "previous_controlled_result_preserved")
        self.assertEqual([call[1] for call in detector.calls], [0.05, 0.03, 0.02, 0.01])

    def test_crowded_inventory_scene_is_accepted(self):
        # 20 ayrı şişe gerçek bir raf sahnesidir; patlama sayılmamalı.
        detector = FakeDetector({0.05: boxes(20, 0.3)})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(result["threshold_selection_reason"], "first_valid_result")
        self.assertEqual(len(result["detections"]), 20)
        self.assertEqual(result["inventory_summary"], {"bag": 20})

    def test_duplicate_overload_uses_raw_and_real_nms_counts(self):
        raw = boxes(1, 0.02) * 20
        detector = FakeDetector({0.01: raw})
        result = run_detection(detector, None, PLAN)
        attempt = result["threshold_attempts"][-1]
        self.assertEqual(attempt["raw_detection_count"], 20)
        self.assertEqual(attempt["filtered_detection_count"], 1)
        self.assertAlmostEqual(attempt["duplicate_fraction"], 0.95)
        self.assertEqual(attempt["assessment"], "duplicate_overload")
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["threshold_selection_reason"], "no_safe_result")
        json.dumps(result, allow_nan=False)

    def test_elapsed_time_includes_all_attempts(self):
        detector = FakeDetector({0.03: boxes(1, 0.1)})
        with patch("backend.app.services.inference_orchestrator.perf_counter", side_effect=[10.0, 10.85]):
            result = run_detection(detector, None, PLAN)
        self.assertAlmostEqual(result["inference_time_ms"], 850)
        self.assertEqual(len(detector.calls), 2)

    def test_all_empty_is_bounded(self):
        detector = FakeDetector({})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(len(detector.calls), 4)
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["threshold_selection_reason"], "no_detections")

    def test_grounding_dino_uses_independent_box_and_text_config(self):
        detector = FakeDetector({0.30: boxes(1, 0.7)}, model_id="grounding-dino")
        result = run_detection(detector, None, PLAN)
        policy = ADAPTIVE_THRESHOLDS["grounding-dino"]
        self.assertEqual(policy.thresholds[0], GROUNDING_DINO.box_threshold)
        self.assertEqual([call[1] for call in detector.calls], [0.35, 0.30])
        self.assertTrue(all(call[2] == GROUNDING_DINO.text_threshold for call in detector.calls))
        self.assertEqual(result["adaptive_threshold_used"], 0.30)
        self.assertEqual(result["threshold_attempts"][0]["text_threshold"], 0.25)

    def test_primary_success_does_not_run_synonym_fallback(self):
        detector = FakeDetector({0.05: boxes(1, 0.2)})
        result = run_detection(detector, None, {**PLAN, "fallback_queries": ["handbag"]})
        self.assertEqual(len(detector.calls), 1)
        self.assertFalse(result["fallback_triggered"])

    def test_nonfinite_score_is_not_accepted(self):
        detector = FakeDetector({0.05: boxes(1, float("nan"))})
        result = run_detection(detector, None, PLAN)
        self.assertEqual(result["threshold_attempts"][0]["assessment"], "invalid_detection")
        self.assertEqual(result["detections"], [])
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
