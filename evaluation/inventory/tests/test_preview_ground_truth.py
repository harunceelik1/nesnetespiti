"""Küçük sentetik görüntülerle GT parsing ve çizim girişlerini doğrular."""

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageColor

from evaluation.inventory.preview_ground_truth import drawing_box, draw_ground_truth, generate_previews, load_annotations, IGNORED_COLOR


def record(name="sample.jpg"):
    return {"file_name": name, "width": 100, "height": 80, "objects": [
        {"evaluation_category": "milk", "bbox_xyxy": [5, 20, 40, 60]},
        {"evaluation_category": "tissue", "bbox_xyxy": [50, 30, 90, 70]},
    ]}


class GroundTruthPreviewTests(unittest.TestCase):
    def test_annotation_list_parsing_skips_invalid_records_and_preserves_objects(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "annotations.json"
            data = [record(), None, {**record("../escape.jpg")}, {**record("bad.jpg"), "width": 0}, record()]
            path.write_text(json.dumps(data), encoding="utf-8")
            warnings = []
            parsed = load_annotations(path, warnings.append)
            self.assertEqual(parsed, [record()])
            self.assertEqual(len(warnings), 4)
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_annotations(path, warnings.append)

    def test_xyxy_inputs_are_checked_and_outside_boxes_are_clipped(self):
        warnings = []
        self.assertEqual(drawing_box([-5, 10, 120, 60], 100, 80, warnings.append, "sample"), (0, 10, 100, 60))
        self.assertEqual(len(warnings), 1)
        for bbox in [[5, 20, 5, 30], [float("nan"), 0, 20, 20], [1, 2, 3], [True, 0, 10, 10], [101, 2, 120, 30]]:
            with self.subTest(bbox=bbox):
                self.assertIsNone(drawing_box(bbox, 100, 80, warnings.append, "sample"))

    def test_all_labels_and_boxes_are_drawn_without_mutating_input(self):
        warnings = []
        with Image.new("RGB", (100, 80), "white") as image:
            original = image.tobytes()
            with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as text:
                with draw_ground_truth(image, record(), warnings.append) as annotated:
                    self.assertNotEqual(annotated.getpixel((5, 50)), (255, 255, 255))
                    self.assertNotEqual(annotated.getpixel((50, 60)), (255, 255, 255))
                labels = [call.args[2] for call in text.call_args_list]
                self.assertEqual(labels[:2], ["milk", "tissue"])
                self.assertEqual(labels[-1], "RPC objects: ? | Selected objects: 2 | Ignored objects: ?")
            self.assertEqual(image.tobytes(), original)
        self.assertEqual(warnings, [])

    def test_bad_object_and_dimension_mismatch_warn_but_keep_valid_box(self):
        data = record()
        data["width"] = 120
        data["objects"].extend([None, {"evaluation_category": "drink", "bbox_xyxy": [0, 0, -1, 5]}])
        warnings = []
        with Image.new("RGB", (100, 80), "white") as image, draw_ground_truth(image, data, warnings.append) as result:
            self.assertEqual(result.size, (100, 80))
        self.assertEqual(len(warnings), 3)

    def test_seeded_previews_use_calibration_only_and_leave_dataset_unchanged(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            calibration = root / "data/calibration"
            images = calibration / "images"
            images.mkdir(parents=True)
            records = [record(f"image-{index}.jpg") for index in range(4)]
            for item in records:
                with Image.new("RGB", (100, 80), "white") as image:
                    image.save(images / item["file_name"])
            annotations = calibration / "annotations.json"
            annotations.write_text(json.dumps(records), encoding="utf-8")
            originals = {path: path.read_bytes() for path in calibration.rglob("*") if path.is_file()}
            for folder in ["one", "two"]:
                with redirect_stderr(StringIO()):
                    report = generate_previews(2, 42, calibration=calibration, output=root / folder)
                self.assertEqual(len(report.files), 2)
                self.assertEqual(report.warnings, [])
            self.assertEqual(sorted(p.name for p in (root / "one").iterdir()), sorted(p.name for p in (root / "two").iterdir()))
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)
            with self.assertRaises(ValueError):
                generate_previews(calibration=calibration, output=images)

    def test_missing_image_warns_and_remaining_image_is_processed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            calibration = root / "data/calibration"
            (calibration / "images").mkdir(parents=True)
            with Image.new("RGB", (100, 80), "white") as image:
                image.save(calibration / "images/ok.jpg")
            (calibration / "annotations.json").write_text(json.dumps([record("ok.jpg"), record("missing.jpg")]))
            with redirect_stderr(StringIO()):
                report = generate_previews(2, calibration=calibration, output=root / "preview")
            self.assertEqual(len(report.files), 1)
            self.assertEqual(len(report.warnings), 1)

    def test_all_mode_draws_ignored_gray_and_reports_true_counts(self):
        data = record()
        full = {**data, "objects": [*data["objects"], {
            "evaluation_category": "alcohol", "original_category_name": "88_alcohol",
            "is_evaluation_category": False, "bbox_xyxy": [65, 40, 95, 75],
        }]}
        warnings = []
        with Image.new("RGB", (100, 80), "white") as image:
            with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as text:
                with draw_ground_truth(image, data, warnings.append, mode="all", full_record=full) as result:
                    self.assertEqual(result.getpixel((95, 65)), ImageColor.getrgb(IGNORED_COLOR))
                labels = [call.args[2] for call in text.call_args_list]
                self.assertEqual(labels[:3], ["milk", "tissue", "alcohol (88_alcohol)"])
                self.assertEqual(labels[-1], "RPC objects: 3 | Selected objects: 2 | Ignored objects: 1")
            with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as text:
                with draw_ground_truth(image, full, warnings.append, mode="selected", full_record=full) as result:
                    self.assertEqual(result.getpixel((95, 65)), (255, 255, 255))
                self.assertEqual([call.args[2] for call in text.call_args_list][:2], ["milk", "tissue"])
                self.assertEqual(len(text.call_args_list), 3)
        self.assertEqual(warnings, [])

    def test_all_mode_refuses_to_treat_selected_subset_as_complete(self):
        with Image.new("RGB", (100, 80)) as image:
            with self.assertRaisesRegex(ValueError, "tam RPC annotation"):
                draw_ground_truth(image, record(), lambda _: None, mode="all")
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            calibration = root / "data/calibration"
            calibration.mkdir(parents=True)
            (calibration / "annotations.json").write_text(json.dumps([record()]))
            with self.assertRaisesRegex(ValueError, "full_annotations.json"):
                generate_previews(1, mode="all", calibration=calibration, output=root / "preview")
            self.assertFalse((root / "preview").exists())

    def test_all_mode_loads_full_file_and_keeps_selected_output_separate(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            calibration = root / "data/calibration"
            (calibration / "images").mkdir(parents=True)
            data = {**record(), "image_id": "fixed-id"}
            with Image.new("RGB", (100, 80), "white") as image:
                image.save(calibration / "images/sample.jpg")
            (calibration / "annotations.json").write_text(json.dumps([data]))
            full = {**data, "objects": [*data["objects"], {"evaluation_category": "alcohol", "bbox_xyxy": [70, 40, 95, 75]}]}
            (calibration.parent / "full_annotations.json").write_text(json.dumps({"complete": True, "image_count": 1, "images": [full]}))
            with redirect_stderr(StringIO()):
                selected = generate_previews(1, calibration=calibration, output=root / "preview")
                all_objects = generate_previews(1, mode="all", calibration=calibration, output=root / "preview")
            self.assertEqual(selected.files[0].name, "sample_ground_truth.jpg")
            self.assertEqual(all_objects.files[0].name, "sample_ground_truth_all.jpg")
            self.assertEqual(all_objects.warnings, [])


if __name__ == "__main__":
    unittest.main()
