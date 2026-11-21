"""Sentetik DINO çıktılarıyla adapter testi; gerçek model veya ağ kullanılmaz."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from evaluation.inventory import evaluate_inventory as evaluation
from evaluation.inventory.grounding_dino_adapter import build_caption, resolve_label
from evaluation.inventory.prompt_aliases import build_prompt_mapping
from evaluation.inventory.tests.test_evaluate_inventory import FakeDetector, annotation


class GroundingDinoAdapterTests(unittest.TestCase):
    def test_canonical_exact_repeated_tokens_and_punctuation(self):
        mapping = build_prompt_mapping(evaluation.CATEGORIES)
        for phrase in ("instant drink", "instant drink drink", "  INSTANT drink drink. "):
            self.assertEqual(resolve_label(phrase, mapping), ("instant drink", "instant drink"))
        self.assertEqual(resolve_label("Milk!", mapping), ("milk", "milk"))
        self.assertEqual(resolve_label("puffed food", mapping), ("puffed food", "puffed food"))

    def test_alias_chain_and_unsafe_labels(self):
        mapping = build_prompt_mapping(evaluation.CATEGORIES, "alias")
        self.assertEqual(resolve_label("milk carton carton.", mapping), ("milk", "milk carton"))
        self.assertEqual(resolve_label("Personal care product", mapping), ("personal hygiene", "personal care product"))
        for phrase in ("unknown product", "milk chocolate", "carton", "milk", "care personal product", ""):
            self.assertIsNone(resolve_label(phrase, mapping))
        self.assertIsNone(resolve_label("drink", {"one": "drink", "two": "drink drink"}))

    def test_caption_has_explicit_phrase_separators(self):
        caption = build_caption(list(evaluation.CATEGORIES))
        self.assertEqual(caption, ". ".join(evaluation.CATEGORIES) + ".")
        self.assertTrue(caption.startswith("puffed food. dried fruit. dried food. instant drink."))
        self.assertEqual(caption.count("."), 17)
        for prompts in ([], [""], ["milk. drink"]):
            with self.assertRaises(ValueError):
                build_caption(prompts)

    def test_unresolved_prediction_preserved_and_five_image_run_continues(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "calibration/images").mkdir(parents=True)
            selected = [annotation(f"cal-{index}") for index in range(5)]
            for record in selected:
                with Image.new("RGB", (24, 24)) as image:
                    image.save(root / "calibration/images" / record["file_name"])
            for mode in ("canonical", "alias"):
                detector = FakeDetector("grounding-dino")
                mapping = build_prompt_mapping(evaluation.CATEGORIES, mode)
                box = {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}
                known = {"label": mapping["milk"] + " " + mapping["milk"].split()[-1], "confidence": .8, "box": box}
                unknown = {"label": "milk chocolate unknown", "confidence": .7, "box": box}
                with patch.object(detector, "infer_queries", return_value=[known, unknown]) as infer, \
                        self.assertWarnsRegex(RuntimeWarning, "Unresolved Grounding DINO"):
                    result = evaluation.evaluate_model(detector, selected, .5, root, prompt_mode=mode)
                self.assertEqual(infer.call_count, 5)
                self.assertEqual(infer.call_args.args[1], list(mapping.values()))
                self.assertEqual(infer.call_args.args[2:], (evaluation.threshold_settings("grounding-dino")["box_threshold"],
                                                           evaluation.threshold_settings("grounding-dino")["text_threshold"]))
                self.assertEqual(result["summary"]["unresolved_model_label_count"], 5)
                self.assertFalse(result["summary"]["label_resolution_complete"])
                self.assertEqual(len(result["unresolved_model_labels"]), 5)
                self.assertEqual(result["unresolved_model_labels"][0]["prediction"], unknown)
                self.assertEqual(result["unresolved_model_labels"][0]["image_id"], "cal-0")
                self.assertEqual(result["summary"]["TP"], 5)
                self.assertEqual(result["summary"]["FN"], 5)
                self.assertEqual(result["summary"]["FP"], 0)
                paths = evaluation.save_results(result, detector.model_id, {}, root / "results")
                saved = json.loads(paths[0].read_text(encoding="utf-8"))
                self.assertEqual(saved["unresolved_model_labels"], result["unresolved_model_labels"])
                self.assertTrue(all(run["model_caption"] == build_caption(list(mapping.values())) for run in saved["image_runs"]))

    def test_owlvit_and_single_query_still_use_strict_matching(self):
        for model, mapping in (("owlvit", build_prompt_mapping(evaluation.CATEGORIES)),
                               ("grounding-dino", {"instant drink": "instant drink"})):
            detector = FakeDetector(model)
            with patch.object(detector, "infer_queries", return_value=[{"label": "instant drink drink"}]):
                with self.assertRaisesRegex(ValueError, "tam eşleşmiyor"):
                    evaluation.infer_categories(detector, None, evaluation.threshold_settings(model), prompt_mapping=mapping)


if __name__ == "__main__":
    unittest.main()
