"""Küçük sentetik kayıtlar/JPEG'ler; ağ ve gerçek RPC verisi kullanılmaz."""

from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from evaluation.inventory import prepare_rpc_subset as rpc
from evaluation.inventory.category_mapping import parse_category_table, semantic_category, xywh_to_xyxy
from evaluation.inventory.config import CATEGORIES, PrepareConfig, SOURCE_FILES, SPLIT, shard_budgets


NAMES = {0: "1_puffed_food", 13: "14_dried_fruit", 96: "97_milk", 78: "79_alcohol"}


def row(index):
    # Her fixture farklı piksel içeriğine sahip, aynı fiziksel görüntü kopyalanmaz.
    with Image.new("RGB", (12, 10), (index * 20, index * 10, index * 5)) as image, BytesIO() as buffer:
        image.save(buffer, format="JPEG")
        return {"image": {"bytes": buffer.getvalue(), "path": None}, "width": 12, "height": 10,
                "objects": {"category": [0 if index % 2 else 13, 96, 96, 78],
                            "bbox": [[0, 0, 2, 3], [3, 2, 2, 2], [6, 3, 2, 2], [0, 0, 1, 1]]}}


class RpcSubsetTests(unittest.TestCase):
    def test_numeric_prefix_and_semantic_mapping(self):
        examples = {"1_puffed_food": "puffed food", "14_dried_fruit": "dried fruit",
                    "22_dried_food": "dried food", "31_instant_drink": "instant drink",
                    "42_instant_noodles": "instant noodles", "71_drink": "drink",
                    "97_milk": "milk", "108_canned_food": "canned food",
                    "122_chocolate": "chocolate", "164_personal_hygiene": "personal hygiene",
                    "174_tissue": "tissue", "194_stationery": "stationery"}
        for original, expected in examples.items():
            with self.subTest(original=original):
                self.assertEqual(semantic_category(original), expected)
        with self.assertRaises(ValueError):
            semantic_category("milk")

    def test_dense_category_id_is_read_from_table_not_name_prefix(self):
        names = parse_category_table("id,original_id,name\n96,,97_milk\n0,,1_puffed_food\n")
        self.assertEqual(names[96], "97_milk")
        self.assertNotIn(97, names)

    def test_xywh_to_xyxy_preserves_pixel_coordinates(self):
        self.assertEqual(xywh_to_xyxy([10.5, 20, 30, 40]), [10.5, 20.0, 40.5, 60.0])
        for bbox in [[1, 2, -1, 4], [1, 2, 0, 4], [1, 2, 3], [float("nan"), 2, 3, 4]]:
            with self.subTest(bbox=bbox), self.assertRaises(ValueError):
                xywh_to_xyxy(bbox)

    def test_multicategory_image_keeps_all_selected_objects_once(self):
        record = rpc.annotation_record(row(0), 0, NAMES)
        self.assertEqual(len(record["objects"]), 3)  # alcohol dışarıda; iki milk kutusu korunur.
        milk = record["objects"][1]
        self.assertEqual(milk["original_category_id"], 96)
        self.assertEqual(milk["original_category_name"], "97_milk")
        self.assertEqual(milk["bbox_xywh"], [3, 2, 2, 2])
        self.assertEqual(milk["bbox_xyxy"], [3, 2, 5, 4])

    def test_seeded_selection_and_disjoint_splits(self):
        records = [rpc.annotation_record(row(i), i, NAMES) for i in range(8)]
        selected = rpc.balanced_select(records, 6, 42)
        self.assertEqual(selected, rpc.balanced_select(records, 6, 42))
        calibration, test = rpc.split_records(selected, 2, 43)
        self.assertEqual(len(calibration), 2)
        self.assertEqual(len(test), 4)
        self.assertFalse({r["image_id"] for r in calibration} & {r["image_id"] for r in test})
        self.assertEqual(rpc.split_records(selected, 2, 43), (calibration, test))
        self.assertTrue({"milk", "puffed food", "dried fruit"} <= set().union(*(rpc.record_categories(r) for r in selected)))

    def test_duplicate_ids_and_pixel_hashes_are_rejected(self):
        record = rpc.annotation_record(row(0), 0, NAMES)
        with self.assertRaises(ValueError):
            rpc.split_records([record, record], 1, 42)
        with self.assertRaises(ValueError):
            rpc.split_records([{**record, "content_sha256": "same"},
                               {**record, "image_id": "other", "content_sha256": "same"}], 1, 42)

    def test_dry_run_never_imports_datasets_downloads_or_writes(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "absent"
            with patch.object(rpc, "prepare", side_effect=AssertionError("No prepare")), redirect_stdout(StringIO()) as stdout:
                self.assertEqual(rpc.main(["--dry-run", "--output", str(output)]), 0)
            plan = json.loads(stdout.getvalue())
            self.assertEqual(plan["split"], "validation")
            self.assertEqual(plan["target_images"], 250)
            self.assertTrue(plan["streaming"])
            self.assertEqual(plan["seed"], 42)
            self.assertEqual(plan["source_files"], list(SOURCE_FILES))
            self.assertEqual(plan["max_scan_rows"], 2000)
            self.assertEqual(list(plan["max_scan_rows_per_shard"].values()), [500] * 4)
            self.assertEqual(list(plan["target_images_per_shard"].values()), [63, 63, 62, 62])
            self.assertFalse(output.exists())

    def test_stream_loader_opens_all_validation_shards_individually(self):
        dataset = MagicMock()
        dataset.cast_column.return_value = dataset
        loader = MagicMock(return_value=dataset)
        fake = SimpleNamespace(load_dataset=loader, Image=MagicMock())
        with patch.dict("sys.modules", {"datasets": fake}):
            for source in SOURCE_FILES:
                rpc.open_stream(images=False, source_file=source)
                args = loader.call_args.kwargs
                self.assertTrue(args["streaming"])
                self.assertEqual(args["split"], SPLIT)
                self.assertEqual(len(args["data_files"][SPLIT]), 1)
                self.assertTrue(args["data_files"][SPLIT][0].endswith(source))
                self.assertNotIn("image", args["columns"])
            rpc.open_stream(images=True, source_file=SOURCE_FILES[0])
            self.assertIn("image", loader.call_args.kwargs["columns"])
            fake.Image.assert_called_once_with(decode=False)
            with self.assertRaises(ValueError):
                rpc.open_stream(images=True, source_file="data/train-00000-of-00036.parquet")

    def test_real_prepare_with_only_tiny_mock_rows_and_manifest(self):
        rows = {source: [row(shard * 8 + i) for i in range(8)] for shard, source in enumerate(SOURCE_FILES)}
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "data"
            config = PrepareConfig(calibration_count=2, test_count=3, max_scan_rows=6, output=output)
            with patch.object(rpc, "read_category_names", return_value=NAMES), patch.object(rpc, "open_stream", side_effect=lambda **kwargs: iter(rows[kwargs["source_file"]])) as stream:
                manifest = rpc.prepare(config)
            self.assertEqual(manifest["total_images"], 5)
            self.assertEqual(manifest["scanned_rows"], 6)
            self.assertEqual(manifest["scanned_rows_per_shard"], shard_budgets(6))
            self.assertEqual(manifest["source_files"], list(SOURCE_FILES))
            self.assertEqual(manifest["selected_images_per_shard"], shard_budgets(5))
            self.assertEqual({call.kwargs["source_file"] for call in stream.call_args_list if not call.kwargs["images"]}, set(SOURCE_FILES))
            self.assertEqual(manifest["category_object_counts"]["milk"], 10)
            self.assertEqual(manifest["category_image_counts"]["milk"], 5)
            self.assertEqual(manifest["category_image_counts"]["stationery"], 0)
            self.assertEqual(manifest["calibration_images"], 2)
            self.assertEqual(manifest["test_images"], 3)
            saved = list(output.rglob("*.jpg"))
            self.assertEqual(len(saved), 5)
            calibration = json.loads((output / "calibration/annotations.json").read_text())
            test = json.loads((output / "test/annotations.json").read_text())
            self.assertEqual(len({r["content_sha256"] for r in calibration + test}), 5)
            for split_name, records in [("calibration", calibration), ("test", test)]:
                for record in records:
                    self.assertTrue((output / split_name / "images" / record["file_name"]).is_file())
            with self.assertRaises(ValueError):
                rpc.prepare(config)  # Önceki hazırlık asla overwrite edilmez.

    def test_pixel_duplicates_or_byte_budget_publish_no_partial_subset(self):
        cases = [([row(0)] * 4, 256 * 1024**2), ([row(i) for i in range(4)], 1)]
        for rows, budget in cases:
            with self.subTest(budget=budget), TemporaryDirectory() as temporary:
                output = Path(temporary) / "data"
                config = PrepareConfig(calibration_count=1, test_count=2, max_scan_rows=4,
                                       max_saved_bytes=budget, output=output)
                with patch.object(rpc, "read_category_names", return_value=NAMES), patch.object(rpc, "open_stream", side_effect=lambda **_: iter(rows)):
                    with self.assertRaises(ValueError):
                        rpc.prepare(config)
                self.assertFalse(output.exists())

    def test_cli_limits_reject_large_jobs_without_network(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()), patch.object(rpc, "prepare") as prepare:
            self.assertEqual(rpc.main(["--test-count", "2000"]), 1)
            self.assertEqual(rpc.main(["--max-scan-rows", "6000"]), 1)
            prepare.assert_not_called()

    def test_all_shards_get_balanced_quotas_and_all_available_categories_are_covered(self):
        records = [
            {"image_id": f"{shard}-{index}", "source_shard": source,
             "objects": [{"evaluation_category": CATEGORIES[index % len(CATEGORIES)]}]}
            for shard, source in enumerate(SOURCE_FILES) for index in range(80)
        ]
        selected = rpc.balanced_select(records, 250, 42, balance_shards=True)
        self.assertEqual(selected, rpc.balanced_select(records, 250, 42, balance_shards=True))
        self.assertEqual(len({record["image_id"] for record in selected}), 250)
        self.assertEqual({source: sum(r["source_shard"] == source for r in selected) for source in SOURCE_FILES}, shard_budgets(250))
        self.assertEqual(set().union(*(rpc.record_categories(r) for r in selected)), set(CATEGORIES))
        calibration, test = rpc.split_records(selected, 50, 43)
        self.assertEqual((len(calibration), len(test)), (50, 200))
        self.assertFalse({r["image_id"] for r in calibration} & {r["image_id"] for r in test})
        self.assertEqual({source: sum(r["source_shard"] == source for r in calibration) for source in SOURCE_FILES}, shard_budgets(50))

    def test_local_row_indexes_from_different_shards_cannot_collide(self):
        records = [rpc.annotation_record(row(0), 0, NAMES, source) for source in SOURCE_FILES]
        self.assertEqual(len({record["image_id"] for record in records}), 4)
        self.assertEqual(len({record["file_name"] for record in records}), 4)

    def test_short_shard_quota_is_redistributed_without_duplicate_selection(self):
        records = [rpc.annotation_record(row(index), index, NAMES, source)
                   for source, size in zip(SOURCE_FILES, [1, 5, 5, 5]) for index in range(size)]
        selected = rpc.balanced_select(records, 12, 42, balance_shards=True)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len({r["image_id"] for r in selected}), 12)
        self.assertEqual(sum(r["source_shard"] == SOURCE_FILES[0] for r in selected), 1)


if __name__ == "__main__":
    unittest.main()
