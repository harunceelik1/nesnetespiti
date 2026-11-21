"""Prompt alias doğrulaması: fake detector ve küçük yerel görüntü; gerçek inference yok."""

import copy
import csv
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from evaluation.inventory import evaluate_inventory as evaluation
from evaluation.inventory.prompt_aliases import PROMPT_ALIASES, build_prompt_mapping
from evaluation.inventory.tests.test_evaluate_inventory import FakeDetector, annotation


EXPECTED = {
    "puffed food": "puffed snack package", "dried fruit": "dried fruit package",
    "dried food": "dried food package", "instant drink": "instant drink package",
    "instant noodles": "instant noodle package", "dessert": "dessert package",
    "drink": "beverage bottle", "alcohol": "alcohol bottle", "milk": "milk carton",
    "canned food": "canned food can", "chocolate": "chocolate package",
    "gum": "chewing gum package", "candy": "candy package", "seasoner": "seasoning package",
    "personal hygiene": "personal care product", "tissue": "tissue pack", "stationery": "stationery item",
}


class AliasDetector(FakeDetector):
    def infer_queries(self, image, queries, threshold, text_threshold):
        detections = super().infer_queries(image, queries, threshold, text_threshold)
        return [{**detection, "label": EXPECTED[detection["label"]]} for detection in detections]


class PromptAliasTests(unittest.TestCase):
    def test_all_aliases_and_canonical_defaults(self):
        self.assertEqual(PROMPT_ALIASES, EXPECTED)
        self.assertEqual(build_prompt_mapping(evaluation.CATEGORIES, "alias"), EXPECTED)
        self.assertEqual(build_prompt_mapping(evaluation.CATEGORIES), {category: category for category in evaluation.CATEGORIES})

    def test_missing_alias_falls_back_to_canonical(self):
        with patch.dict(PROMPT_ALIASES, {"milk": "milk carton"}, clear=True):
            mapping = build_prompt_mapping(evaluation.CATEGORIES, "alias")
        self.assertEqual(mapping["milk"], "milk carton")
        self.assertTrue(all(mapping[category] == category for category in evaluation.CATEGORIES if category != "milk"))

    def test_ambiguous_alias_collision_is_rejected(self):
        with patch.dict(PROMPT_ALIASES, {"milk": "beverage bottle"}):
            with self.assertRaisesRegex(ValueError, "aynı model prompt"):
                build_prompt_mapping(evaluation.CATEGORIES, "alias")
        with self.assertRaises(ValueError):
            build_prompt_mapping(evaluation.CATEGORIES, "invalid")

    def test_alias_is_reversed_before_nms_matching_and_exports_preserve_category(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "calibration/images").mkdir(parents=True)
            with Image.new("RGB", (24, 24)) as image:
                image.save(root / "calibration/images/cal-a.jpg")
            selected = [annotation()]
            before = copy.deepcopy(selected)
            for model in ("owlvit", "grounding-dino"):
                with self.subTest(model=model):
                    canonical_detector, alias_detector = FakeDetector(model), AliasDetector(model)
                    with patch.object(evaluation, "perf_counter", side_effect=[10.0, 10.5, 20.0, 20.5]):
                        canonical = evaluation.evaluate_model(canonical_detector, selected, 0.5, root)
                        alias = evaluation.evaluate_model(alias_detector, selected, 0.5, root, prompt_mode="alias")
                    self.assertEqual(selected, before)
                    self.assertEqual(len(alias_detector.calls), 1)
                    self.assertEqual(alias_detector.calls[0][0], list(EXPECTED.values()))
                    self.assertEqual(alias_detector.calls[0][1:], canonical_detector.calls[0][1:])
                    self.assertEqual(alias["summary"]["prompt_mode"], "alias")
                    self.assertEqual(alias["summary"]["category_prompt_mapping"], EXPECTED)
                    for key in canonical["summary"]:
                        if key not in ("prompt_mode", "category_prompt_mapping", "total_evaluation_time_ms"):
                            self.assertEqual(alias["summary"][key], canonical["summary"][key])
                    rows = {row["category"]: row for row in alias["records"]}
                    self.assertEqual(set(rows), set(evaluation.CATEGORIES))
                    self.assertEqual(rows["milk"]["model_prompt"], "milk carton")
                    self.assertEqual(rows["milk"]["TP"], 1)
                    self.assertEqual(rows["milk"]["predicted_count"], 1)  # NMS yine canonical label üzerinde.
                    self.assertEqual(rows["alcohol"]["ground_truth_count"], 1)
                    self.assertTrue(all(row["prompt_mode"] == "alias" for row in rows.values()))
                    prediction = alias["image_runs"][0]["detections"][0]
                    self.assertEqual(prediction["label"], "milk")
                    self.assertEqual(prediction["raw_model_label"], "milk carton")
                    paths = evaluation.save_results(alias, model, {}, root / "results")
                    self.assertIn("_alias_", paths[0].name)
                    exported = json.loads(paths[0].read_text())
                    self.assertEqual(exported["metadata"]["prompt_mode"], "alias")
                    self.assertEqual(exported["summary"]["category_prompt_mapping"], EXPECTED)
                    with paths[1].open(newline="", encoding="utf-8") as file:
                        csv_rows = {row["category"]: row for row in csv.DictReader(file)}
                    self.assertEqual(csv_rows["milk"]["model_prompt"], "milk carton")
                    self.assertEqual(csv_rows["milk"]["prompt_mode"], "alias")

    def test_cli_modes_keep_identical_selection_and_never_load_models_in_dry_run(self):
        plans = []
        with patch.object(evaluation, "load_calibration", return_value=([annotation()], {})) as load, \
                patch.object(evaluation, "make_detector", side_effect=AssertionError("No inference")) as factory:
            for mode in ("canonical", "alias"):
                with redirect_stdout(StringIO()) as stdout:
                    self.assertEqual(evaluation.main(["--limit", "1", "--prompt-mode", mode, "--dry-run"]), 0)
                    plans.append(json.loads(stdout.getvalue()))
            self.assertEqual([call.args for call in load.call_args_list], [(1, 42), (1, 42)])
            factory.assert_not_called()
        self.assertEqual(plans[0]["image_ids"], plans[1]["image_ids"])
        self.assertEqual(plans[0]["model_thresholds"], plans[1]["model_thresholds"])
        self.assertEqual(plans[1]["category_prompt_mapping"], EXPECTED)


if __name__ == "__main__":
    unittest.main()
