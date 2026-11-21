"""Tam annotation recovery: sadece küçük mock stream'ler, gerçek ağ erişimi yok."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from evaluation.inventory import recover_full_annotations as recovery
from evaluation.inventory.config import SOURCE_FILES, REVISION, DATASET
from evaluation.inventory.prepare_rpc_subset import annotation_record


def fixture(data: Path):
    names = {96: "97_milk", 87: "88_alcohol"}
    source_row = {"width": 100, "height": 100, "objects": {"category": [96, 87], "bbox": [[1, 2, 10, 20], [30, 40, 20, 25]]}}
    records = [annotation_record(source_row, 0, names, source) for source in SOURCE_FILES]
    split_ids = {}
    for split, items in [("calibration", records[:2]), ("test", records[2:])]:
        (data / split / "images").mkdir(parents=True)
        (data / split / "annotations.json").write_text(json.dumps(items))
        split_ids[split] = [item["image_id"] for item in items]
        for item in items:
            (data / split / "images" / item["file_name"]).write_bytes(b"JPEG must not be opened or changed")
    manifest = {"status": "prepared", "dataset": DATASET, "split": "validation", "revision": REVISION,
                "split_image_ids": split_ids, "total_images": 4,
                "category_mapping": {str(key): {"original_name": value} for key, value in names.items()}}
    (data / "manifest.json").write_text(json.dumps(manifest))
    return source_row, records


class RecoverFullAnnotationsTests(unittest.TestCase):
    def test_recovery_reads_only_metadata_and_preserves_existing_files_and_ids(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            source_row, records = fixture(data)
            protected = {path: path.read_bytes() for path in data.rglob("*") if path.is_file()}
            with patch.object(recovery, "open_stream", side_effect=lambda **_: iter([source_row])) as stream:
                result = recovery.recover(data)
            self.assertEqual(stream.call_count, 4)
            self.assertTrue(all(call.kwargs["images"] is False for call in stream.call_args_list))
            self.assertEqual([r["image_id"] for r in result["images"]], [r["image_id"] for r in records])
            self.assertEqual(result["image_count"], 4)
            self.assertEqual(result["scanned_rows"], 4)
            self.assertTrue(result["complete"])
            for record in result["images"]:
                self.assertEqual(len(record["objects"]), 2)
                self.assertEqual([o["is_evaluation_category"] for o in record["objects"]], [True, False])
                ignored = record["objects"][1]
                self.assertEqual(ignored["original_category_name"], "88_alcohol")
                self.assertEqual(ignored["bbox_xyxy"], [30, 40, 50, 65])
            self.assertEqual({path: path.read_bytes() for path in protected}, protected)
            self.assertTrue((data / "full_annotations.json").exists())
            with self.assertRaisesRegex(ValueError, "üzerine"):
                recovery.recover(data)

    def test_plan_is_local_and_bounded_by_existing_source_positions(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            fixture(data)
            with patch.object(recovery, "open_stream", side_effect=AssertionError("Network forbidden")):
                plan = recovery.recovery_plan(data)
            self.assertEqual(plan["image_count"], 4)
            self.assertEqual(plan["max_rows_read"], 4)
            self.assertNotIn("image", plan["columns"])
            self.assertFalse((data / "full_annotations.json").exists())

    def test_wrong_source_annotations_are_rejected_without_output(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            source_row, _ = fixture(data)
            source_row["objects"]["bbox"][0] = [0, 0, 5, 5]
            with patch.object(recovery, "open_stream", return_value=iter([source_row])):
                with self.assertRaisesRegex(ValueError, "uyuşmuyor"):
                    recovery.recover(data)
            self.assertFalse((data / "full_annotations.json").exists())

    def test_manifest_id_drift_is_rejected_before_any_network(self):
        with TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            fixture(data)
            manifest = json.loads((data / "manifest.json").read_text())
            manifest["split_image_ids"]["test"][0] = "wrong-id"
            (data / "manifest.json").write_text(json.dumps(manifest))
            with patch.object(recovery, "open_stream") as stream:
                with self.assertRaises(ValueError):
                    recovery.recover(data)
                stream.assert_not_called()


if __name__ == "__main__":
    unittest.main()
