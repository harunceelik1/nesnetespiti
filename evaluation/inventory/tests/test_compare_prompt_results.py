import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from evaluation.inventory.compare_prompt_results import compare_results, main
from evaluation.inventory.evaluate_inventory import CATEGORIES


def report(mode):
    return {"metadata": {"split": "calibration", "prompt_mode": mode, "model": "owlvit",
                         "inference_mode": "single-query", "seed": 42, "dataset": "mock",
                         "revision": "mock", "full_annotations_sha256": "mock", "manifest_sha256": "mock",
                         "categories": list(CATEGORIES)},
            "records": [{"image_id": str(index), "category": category, "TP": 1, "FP": 0, "FN": 0,
                         "ground_truth_count": 1, "predicted_count": 1,
                         "threshold": {"confidence_threshold": .05}, "matching_iou_threshold": .5,
                         "model": "owlvit", "inference_mode": "single-query"}
                        for index in range(5) for category in CATEGORIES]}


class ComparisonTests(unittest.TestCase):
    def test_aggregated_counts_delta_and_consistency(self):
        canonical, alias = report("canonical"), report("alias")
        alias["records"][0].update(TP=0, FP=3, FN=1, predicted_count=3)
        before = copy.deepcopy(alias)
        result = compare_results(canonical, alias)
        row = result["records"][0]
        self.assertEqual(row["canonical_TP"], 5)
        self.assertEqual(row["alias_TP"], 4)
        self.assertEqual(row["alias_FP"], 3)
        self.assertAlmostEqual(row["alias_F1"], 8/12)
        self.assertAlmostEqual(row["F1_delta"], 8/12 - 1)
        self.assertEqual(row["worsened_images"], 1)
        self.assertEqual(row["unchanged_images"], 4)
        self.assertEqual(alias, before)

    def test_mismatched_conditions_and_duplicate_records_rejected(self):
        for field, value in (("inference_mode", "multi-label"), ("seed", 7), ("model", "grounding-dino")):
            alias = report("alias")
            alias["metadata"][field] = value
            with self.assertRaises(ValueError):
                compare_results(report("canonical"), alias)
        for field, value in (("image_id", "other"), ("threshold", {}), ("ground_truth_count", 2)):
            alias = report("alias")
            alias["records"][0][field] = value
            with self.assertRaises(ValueError):
                compare_results(report("canonical"), alias)
        alias = report("alias")
        alias["records"].append(alias["records"][0])
        with self.assertRaises(ValueError):
            compare_results(report("canonical"), alias)

    def test_cli_prints_and_saves_without_changing_sources(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mode in ("canonical", "alias"):
                (root / f"{mode}.json").write_text(json.dumps(report(mode)), encoding="utf-8")
            sources = {path: path.read_bytes() for path in root.glob("*.json")}
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(main(["--canonical", str(root / "canonical.json"), "--alias", str(root / "alias.json"),
                                       "--output-dir", str(root / "comparisons")]), 0)
            self.assertIn("F1 delta", output.getvalue())
            self.assertEqual(len(list((root / "comparisons").glob("*.json"))), 1)
            self.assertEqual(len(list((root / "comparisons").glob("*.csv"))), 1)
            self.assertTrue(all(path.read_bytes() == content for path, content in sources.items()))


if __name__ == "__main__":
    unittest.main()
