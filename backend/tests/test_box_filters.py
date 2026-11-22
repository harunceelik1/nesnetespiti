"""Parça kutusu temizliği: büyük kutunun içindeki küçük kutu atılır, komşu kutular kalır."""

import unittest
from unittest.mock import patch

from backend.app import config
from backend.app.models.base_detector import BaseDetector
from backend.app.services.inference_orchestrator import run_detection
from backend.app.utils.box_filters import clean_boxes


def det(score, x1, y1, x2, y2, label="snack", **extra):
    return {"label": label, "confidence": score, "box": {"xmin": x1, "ymin": y1, "xmax": x2, "ymax": y2}, **extra}


class CleanBoxesTests(unittest.TestCase):
    def test_part_inside_higher_scored_box_is_dropped(self):
        bag, part = det(0.4, 0, 0, 100, 100), det(0.2, 10, 10, 40, 40)
        self.assertEqual(clean_boxes([part, bag], max_containment=0.7), [bag])

    def test_neighbours_and_other_labels_survive(self):
        a, b = det(0.4, 0, 0, 100, 100), det(0.3, 90, 0, 190, 100)   # %10 örtüşme
        other = det(0.2, 10, 10, 40, 40, label="can")                 # farklı etiket
        self.assertEqual(clean_boxes([a, b, other], max_containment=0.7), [a, b, other])

    def test_higher_scored_inner_box_is_kept(self):
        # İçteki kutu daha emin: içerideki tutulur, dıştaki (bölge) kutu da kalır.
        inner, outer = det(0.5, 10, 10, 40, 40), det(0.2, 0, 0, 100, 100)
        self.assertEqual(clean_boxes([outer, inner], max_containment=0.7), [inner, outer])

    def test_objectness_only_applies_when_reported(self):
        low, unknown = det(0.4, 0, 0, 10, 10, objectness=0.01), det(0.3, 50, 50, 60, 60)
        self.assertEqual(clean_boxes([low, unknown], min_objectness=0.05), [unknown])

    def test_region_box_around_two_kept_boxes(self):
        a, b, region = det(0.5, 0, 0, 40, 40), det(0.4, 60, 0, 100, 40), det(0.3, 0, 0, 100, 40)
        self.assertEqual(clean_boxes([a, b, region], drop_regions=True), [a, b])


class SceneBoxOrderTests(unittest.TestCase):
    """Görselin tamamını saran sahne kutusu, içindeki gerçek kutuyu sildirmemeli."""

    class Fake(BaseDetector):
        model_id, name, response_model = "grounding-dino", "fake", "fake"

        def _infer_raw(self, image, queries, threshold):
            return [det(0.9, 0, 0, 100, 100, label=queries[0]), det(0.6, 20, 20, 50, 50, label=queries[0])]

    def test_real_box_survives_full_scene_box(self):
        from PIL import Image
        plan = {"original_query": "snack", "detected_language": "en", "translated_query": None,
                "primary_query": "snack", "fallback_queries": []}
        with patch.object(config, "PART_BOX_CONTAINMENT", 0.7):
            result = run_detection(self.Fake(), Image.new("RGB", (100, 100)), plan)
        self.assertEqual([d["box"]["xmin"] for d in result["detections"]], [20])


if __name__ == "__main__":
    unittest.main()
