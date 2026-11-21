"""Yalnızca fake detector ve sentetik görüntüler; model yüklemez."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from evaluation.inventory import evaluate_inventory as evaluation
from evaluation.inventory.prompt_aliases import build_prompt_mapping
from evaluation.inventory.tests.test_evaluate_inventory import annotation


class QueryDetector:
    model_id = "owlvit"
    device = "cpu"

    def __init__(self):
        self.calls = []

    def infer_queries(self, image, queries, threshold, text_threshold):
        self.calls.append((queries, threshold, text_threshold))
        # Aynı kutu farklı kategori sorgularında da dönebilir; çapraz TP olmamalı.
        return [{"label": query, "confidence": 0.8,
                 "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}} for query in queries]


class InferenceModeTests(unittest.TestCase):
    def test_modes_models_and_prompts_keep_canonical_matching_and_settings(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "calibration/images").mkdir(parents=True)
            with Image.new("RGB", (24, 24)) as image:
                image.save(root / "calibration/images/cal-a.jpg")
            for model in ("owlvit", "grounding-dino"):
                for prompt_mode in ("canonical", "alias"):
                    results = []
                    for mode, count in (("multi-label", 1), ("single-query", 17)):
                        detector = QueryDetector()
                        detector.model_id = model
                        with patch.object(evaluation, "perf_counter", side_effect=[float(i) for i in range(count * 2)]):
                            result = evaluation.evaluate_model(detector, [annotation()], .5, root,
                                                               prompt_mode=prompt_mode, inference_mode=mode)
                        results.append(result)
                        self.assertEqual(len(detector.calls), count)
                        self.assertEqual(result["summary"]["total_forward_calls"], count)
                        self.assertEqual(result["summary"]["inference_mode"], mode)
                        self.assertGreaterEqual(result["summary"]["total_evaluation_time_ms"], 0)
                        mapping = build_prompt_mapping(evaluation.CATEGORIES, prompt_mode)
                        self.assertEqual([q for call in detector.calls for q in call[0]], list(mapping.values()))
                        settings = evaluation.threshold_settings(model)
                        self.assertTrue(all(call[1:] == (settings.get("confidence_threshold", settings.get("box_threshold")), settings.get("text_threshold")) for call in detector.calls))
                        for row in result["records"]:
                            self.assertEqual(row["category_inference_time_ms"], 1000.0 if count == 17 else None)
                        rows = {row["category"]: row for row in result["records"]}
                        self.assertEqual(rows["milk"]["TP"], 1)
                        self.assertEqual(rows["candy"]["TP"], 0)
                        self.assertEqual(rows["candy"]["FP"], 1)
                        paths = evaluation.save_results(result, model, {}, root / "results")
                        saved = json.loads(paths[0].read_text(encoding="utf-8"))
                        self.assertEqual(saved["metadata"]["inference_mode"], mode)
                    for field in ("TP", "FP", "FN", "micro_F1", "per_category"):
                        self.assertEqual(results[0]["summary"][field], results[1]["summary"][field])

    def test_dry_run_counts_and_same_selection(self):
        with patch.object(evaluation, "load_calibration", return_value=([annotation()] * 5, {})), \
                patch.object(evaluation, "make_detector", side_effect=AssertionError("No models")) as factory:
            plans = []
            for mode, count in (("multi-label", 10), ("single-query", 170)):
                with redirect_stdout(StringIO()) as output:
                    self.assertEqual(evaluation.main(["--dry-run", "--model", "both", "--inference-mode", mode]), 0)
                plan = json.loads(output.getvalue())
                self.assertEqual(plan["max_forward_calls"], count)
                plans.append(plan)
            factory.assert_not_called()
            self.assertEqual(plans[0]["image_ids"], plans[1]["image_ids"])

    def test_single_query_rejects_other_label_and_invalid_mode(self):
        detector = QueryDetector()
        with patch.object(detector, "infer_queries", return_value=[{"label": "milk", "confidence": .8, "box": {}}]):
            with self.assertRaisesRegex(ValueError, "tam eşleşmiyor"):
                evaluation.infer_image(detector, None, evaluation.threshold_settings("owlvit"),
                                       {"candy": "candy"}, "canonical", "single-query")
        with self.assertRaises(ValueError):
            evaluation.infer_image(detector, None, {}, {}, "canonical", "invalid")


if __name__ == "__main__":
    unittest.main()
