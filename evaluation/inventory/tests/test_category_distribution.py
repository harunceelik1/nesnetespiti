"""Dağılım sayımları; dosya/ağ/model erişimi gerektirmez."""

import unittest

from evaluation.inventory.analyze_category_distribution import analyze_distribution


class CategoryDistributionTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"complete": True, "image_count": 2, "images": [
            {"image_id": "a", "subset": "calibration", "objects": [
                {"evaluation_category": "milk", "is_evaluation_category": True},
                {"evaluation_category": "milk", "is_evaluation_category": True},
                {"evaluation_category": "alcohol", "is_evaluation_category": False},
            ]},
            {"image_id": "b", "subset": "test", "objects": [
                {"evaluation_category": "alcohol", "is_evaluation_category": False},
                {"evaluation_category": "previously unseen family", "is_evaluation_category": False},
            ]},
        ]}
        self.splits = {"calibration": ["a"], "test": ["b"]}

    def test_discovers_all_families_and_counts_unique_images_not_objects(self):
        result = analyze_distribution(self.payload, self.splits)
        rows = {r["semantic_category"]: r for r in result["categories"]}
        self.assertEqual(set(rows), {"milk", "alcohol", "previously unseen family"})
        self.assertEqual((rows["milk"]["image_count"], rows["milk"]["object_count"]), (1, 2))
        self.assertEqual((rows["alcohol"]["calibration_image_count"], rows["alcohol"]["test_image_count"]), (1, 1))
        self.assertEqual(result["summary"]["total_objects"], 5)
        self.assertEqual(result["summary"]["average_objects_per_annotation"], 2.5)

    def test_duplicate_or_mismatched_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze_distribution(self.payload, {"calibration": ["a"], "test": ["a"]})
        self.payload["images"][1]["image_id"] = "a"
        with self.assertRaises(ValueError):
            analyze_distribution(self.payload, self.splits)

    def test_invalid_split_or_missing_family_is_rejected(self):
        self.payload["images"][0]["subset"] = "test"
        with self.assertRaises(ValueError):
            analyze_distribution(self.payload, self.splits)
        self.payload["images"][0]["subset"] = "calibration"
        self.payload["images"][0]["objects"][0].pop("evaluation_category")
        with self.assertRaises(ValueError):
            analyze_distribution(self.payload, self.splits)


if __name__ == "__main__":
    unittest.main()
