"""Yalnızca sentetik kutularla metric doğrulaması; model/dataset erişimi yok."""

import unittest

from evaluation.inventory.metrics import evaluate_boxes, iou, summarize


BOX = [0, 0, 10, 10]


def pred(box=BOX, confidence=0.9):
    return {"box": box, "confidence": confidence}


class InventoryMetricsTests(unittest.TestCase):
    def test_iou_exact_partial_disjoint_and_zero_area(self):
        self.assertEqual(iou(BOX, BOX), 1)
        self.assertAlmostEqual(iou(BOX, [5, 0, 15, 10]), 1 / 3)
        self.assertEqual(iou(BOX, [20, 20, 30, 30]), 0)
        self.assertEqual(iou([0, 0, 0, 0], [0, 0, 0, 0]), 0)

    def test_perfect_prediction(self):
        result = evaluate_boxes([pred()], [BOX])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (1, 0, 0))
        self.assertEqual((result["precision"], result["recall"], result["F1"]), (1, 1, 1))
        self.assertEqual(result["average_matched_iou"], 1)
        self.assertEqual(result["count_absolute_error"], 0)

    def test_duplicate_prediction_cannot_reuse_ground_truth(self):
        result = evaluate_boxes([pred(confidence=0.7), pred(confidence=0.9)], [BOX])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (1, 1, 0))
        self.assertEqual(result["matches"][0]["prediction_index"], 1)
        self.assertEqual(result["count_absolute_error"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1)
        self.assertAlmostEqual(result["F1"], 2 / 3)

    def test_prediction_cannot_match_two_ground_truth_boxes(self):
        result = evaluate_boxes([pred()], [BOX, BOX])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (1, 0, 1))
        self.assertEqual(result["matches"][0]["ground_truth_index"], 0)

    def test_iou_threshold_inclusive_and_stable_ties(self):
        result = evaluate_boxes([pred(), pred()], [[0, 0, 5, 10], BOX], iou_threshold=0.5)
        self.assertEqual(result["TP"], 2)
        self.assertEqual(result["matches"], [
            {"prediction_index": 0, "ground_truth_index": 1, "iou": 1.0},
            {"prediction_index": 1, "ground_truth_index": 0, "iou": 0.5},
        ])
        self.assertEqual(result["average_matched_iou"], 0.75)
        self.assertEqual(evaluate_boxes([pred()], [[0, 0, 5, 10]])["TP"], 1)
        self.assertEqual(evaluate_boxes([pred()], [[0, 0, 5, 10]], 0.51)["TP"], 0)

    def test_same_counts_but_wrong_location_has_zero_count_error_and_bad_detection(self):
        result = evaluate_boxes([pred([50, 50, 60, 60])], [BOX])
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (0, 1, 1))
        self.assertEqual(result["count_absolute_error"], 0)
        self.assertIsNone(result["average_matched_iou"])

    def test_empty_predictions_or_ground_truth(self):
        for predictions, gt, expected in [([], [BOX], (0, 0, 1)), ([pred()], [], (0, 1, 0)), ([], [], (0, 0, 0))]:
            with self.subTest(expected=expected):
                result = evaluate_boxes(predictions, gt)
                self.assertEqual(tuple(result[key] for key in ("TP", "FP", "FN")), expected)
                self.assertEqual(result["F1"], 0)

    def test_invalid_threshold_boxes_and_confidence(self):
        for threshold in [0, 1.1, float("nan")]:
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                evaluate_boxes([], [], threshold)
        with self.assertRaises(ValueError):
            iou([10, 0, 0, 10], BOX)
        with self.assertRaises(ValueError):
            evaluate_boxes([pred(confidence=float("nan"))], [BOX])

    def test_micro_macro_weighted_iou_and_image_level_timing(self):
        rows = [
            {"category": "milk", **evaluate_boxes([pred()], [BOX])},
            {"category": "milk", **evaluate_boxes([pred()], [BOX])},
            {"category": "alcohol", **evaluate_boxes([pred([0, 0, 5, 10]), pred(confidence=0.1)], [BOX])},
            {"category": "alcohol", **evaluate_boxes([], [BOX])},
        ]
        summary = summarize(rows, ("milk", "alcohol"), [{"inference_time_ms": 10}, {"inference_time_ms": 30}])
        self.assertEqual((summary["TP"], summary["FP"], summary["FN"]), (3, 1, 1))
        self.assertEqual(summary["micro_F1"], 0.75)
        self.assertEqual(summary["macro_F1"], 0.75)
        self.assertAlmostEqual(summary["mean_matched_iou"], 2.5 / 3)
        self.assertEqual(summary["mean_absolute_counting_error"], 0.5)
        self.assertEqual(summary["average_inference_time_ms"], 20)


if __name__ == "__main__":
    unittest.main()
