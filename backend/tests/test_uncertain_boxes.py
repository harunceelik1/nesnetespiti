import unittest

from PIL import Image

from backend.app import config
from backend.app.services.inventory_service import add_inventory, mark_uncertain
from backend.app.utils.visualization import CERTAIN_COLOR, UNCERTAIN_COLOR, annotate_image


def det(label, confidence, left=0, canonical=None):
    return {"label": label, "canonical_query": canonical or label, "confidence": confidence,
            "box": {"xmin": left, "ymin": 10, "xmax": left + 40, "ymax": 50}}


class UncertainBoxTests(unittest.TestCase):
    def test_boxes_below_half_of_best_are_marked_not_removed(self):
        # Saç spreyi örneği: 0.44 doğru şişe, 0.19'luk iki kutu şüpheli.
        result = mark_uncertain([det("hairspray", .44), det("hairspray", .19, 50), det("hairspray", .22, 100)])
        self.assertEqual([d["uncertain"] for d in result], [False, True, False])
        self.assertEqual(len(result), 3)

    def test_each_query_is_compared_with_its_own_best(self):
        result = mark_uncertain([det("gum", .9), det("gum", .3, 50), det("bottle", .2, 100), det("bottle", .15, 150)])
        self.assertEqual([d["uncertain"] for d in result], [False, True, False, False])

    def test_ratio_comes_from_config(self):
        self.assertEqual(config.UNCERTAIN_RELATIVE_RATIO, 0.5)
        result = mark_uncertain([det("a", .4), det("a", .3, 50)], ratio=0.8)
        self.assertEqual([d["uncertain"] for d in result], [False, True])

    def test_inventory_still_counts_uncertain_boxes(self):
        result = add_inventory({"detections": [det("gum", .9), det("gum", .2, 50)]}, ["gum"])
        self.assertEqual(result["inventory_summary"], {"gum": 2})
        self.assertEqual(result["total_detected_objects"], 2)
        self.assertEqual([d["uncertain"] for d in result["detections"]], [False, True])

    def test_uncertain_box_is_dashed_and_orange(self):
        image = Image.new("RGB", (200, 80), "white")
        annotated = annotate_image(image, [{**det("a", .9), "uncertain": False},
                                           {**det("a", .2, 120), "uncertain": True}])
        orange = Image.new("RGB", (1, 1), UNCERTAIN_COLOR).getpixel((0, 0))
        red = Image.new("RGB", (1, 1), CERTAIN_COLOR).getpixel((0, 0))
        # Kesin kutunun alt kenarı kesintisiz kırmızı; şüpheli kutunun alt kenarında boşluklar var.
        certain_edge = [annotated.getpixel((x, 50)) for x in range(2, 38)]
        uncertain_edge = [annotated.getpixel((x, 50)) for x in range(122, 158)]
        self.assertTrue(all(p == red for p in certain_edge))
        self.assertIn(orange, uncertain_edge)
        self.assertIn((255, 255, 255), uncertain_edge)


if __name__ == "__main__":
    unittest.main()
