"""Fake detector + minik yerel görüntüler; gerçek model yüklenmez."""

from contextlib import redirect_stderr, redirect_stdout
import csv
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from evaluation.inventory import evaluate_inventory as evaluation


def annotation(image_id="cal-a", subset="calibration"):
    return {"image_id": image_id, "file_name": image_id + ".jpg", "subset": subset,
            "width": 24, "height": 24, "objects": [
                {"evaluation_category": "milk", "bbox_xyxy": [0, 0, 10, 10], "is_evaluation_category": True},
                {"evaluation_category": "alcohol", "bbox_xyxy": [12, 0, 20, 10], "is_evaluation_category": False},
            ]}


class FakeDetector:
    device = "cpu"

    def __init__(self, model_id):
        self.model_id = model_id
        self.calls = []

    def infer_queries(self, image, queries, threshold, text_threshold):
        self.calls.append((queries, threshold, text_threshold))
        return [
            {"label": "milk", "confidence": 0.9, "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}},
            {"label": "milk", "confidence": 0.8, "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}},
            {"label": "candy", "confidence": 0.7, "box": {"xmin": 12, "ymin": 0, "xmax": 20, "ymax": 10}},
        ]


class EvaluateInventoryTests(unittest.TestCase):
    def test_one_multicategory_call_preserves_labels_counts_absent_classes_and_reuses_nms(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary)
            (data / "calibration/images").mkdir(parents=True)
            with Image.new("RGB", (24, 24)) as image:
                image.save(data / "calibration/images/cal-a.jpg")
            for model_id in ("owlvit", "grounding-dino"):
                with self.subTest(model=model_id):
                    detector = FakeDetector(model_id)
                    result = evaluation.evaluate_model(detector, [annotation()], 0.5, data)
                    self.assertEqual(len(detector.calls), 1)
                    self.assertEqual(detector.calls[0][0], list(evaluation.CATEGORIES))
                    self.assertEqual(len(result["records"]), 17)
                    rows = {row["category"]: row for row in result["records"]}
                    self.assertEqual(rows["milk"]["TP"], 1)
                    self.assertEqual(rows["milk"]["predicted_count"], 1)  # NMS reused.
                    self.assertEqual(rows["alcohol"]["FN"], 1)  # Eski 13-kategori flag'i kullanılmaz.
                    self.assertEqual(rows["candy"]["FP"], 1)  # Görüntüde olmayan kategorinin FP'si sayılır.
                    self.assertEqual(result["summary"]["micro_F1"], 0.5)
                    if model_id == "owlvit":
                        self.assertEqual(detector.calls[0][1:], (0.05, None))
                    else:
                        from backend.app.config import GROUNDING_DINO
                        self.assertEqual(detector.calls[0][1:], (GROUNDING_DINO.box_threshold, GROUNDING_DINO.text_threshold))
                    paths = evaluation.save_results(result, model_id, {"split": "calibration"}, data / "results")
                    report = json.loads(paths[0].read_text())
                    self.assertFalse(report["metadata"]["production_adaptive_threshold_used"])
                    with paths[1].open(newline="", encoding="utf-8") as file:
                        csv_rows = list(csv.DictReader(file))
                    self.assertEqual(len(csv_rows), 17)
                    self.assertEqual(json.loads(csv_rows[0]["threshold"])["strategy"], "fixed_smoke_baseline")

    def test_loader_uses_only_calibration_and_is_seeded(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary)
            (data / "calibration/images").mkdir(parents=True)
            records = [annotation("cal-" + str(i)) for i in range(3)]
            test = annotation("test-a", "test")
            test["objects"] = [{"evaluation_category": "test-only-label-must-not-affect-prompts"}]
            for record in records:
                with Image.new("RGB", (24, 24)) as image:
                    image.save(data / "calibration/images" / record["file_name"])
            full = {"complete": True, "dataset": "finedet/rpc", "revision": "fixed", "image_count": 4, "images": [*records, test]}
            manifest = {"revision": "fixed", "split_image_ids": {"calibration": [r["image_id"] for r in records], "test": ["test-a"]}}
            (data / "full_annotations.json").write_text(json.dumps(full))
            (data / "manifest.json").write_text(json.dumps(manifest))
            first, metadata = evaluation.load_calibration(2, 42, data)
            self.assertEqual(first, evaluation.load_calibration(2, 42, data)[0])
            self.assertEqual(len(first), 2)
            self.assertTrue(all(r["subset"] == "calibration" for r in first))
            self.assertEqual(metadata["split"], "calibration")
            with self.assertRaises(ValueError):
                evaluation.load_calibration(6, 42, data)

    def test_ambiguous_labels_are_not_silently_dropped(self):
        detector = FakeDetector("owlvit")
        detector.infer_queries = lambda *args: [{"label": "drink milk combined phrase", "confidence": 0.9,
                                               "box": {"xmin": 0, "ymin": 0, "xmax": 1, "ymax": 1}}]
        with self.assertRaisesRegex(ValueError, "tam eşleşmiyor"):
            evaluation.infer_categories(detector, None, evaluation.threshold_settings("owlvit"))

    def test_cli_refuses_test_split_or_limit_over_five_before_model_loading(self):
        for args in (["--split", "test"], ["--limit", "6"]):
            with self.subTest(args=args), patch.object(evaluation, "make_detector") as factory, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    evaluation.main(args)
                factory.assert_not_called()
        with self.assertRaises(ValueError):
            evaluation.evaluate_model(FakeDetector("owlvit"), [annotation("test", "test")], 0.5)

    def test_dry_run_cannot_load_a_model_or_write_results(self):
        with patch.object(evaluation, "load_calibration", return_value=([annotation()], {})), \
                patch.object(evaluation, "make_detector", side_effect=AssertionError("Model loading forbidden")), \
                patch.object(evaluation, "save_results", side_effect=AssertionError("Writes forbidden")), redirect_stdout(StringIO()) as stdout:
            self.assertEqual(evaluation.main(["--model", "both", "--limit", "1", "--dry-run"]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["max_forward_calls"], 2)


if __name__ == "__main__":
    unittest.main()
