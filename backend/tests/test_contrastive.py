"""Karşıt sorgu: olmayan nesne uydurmasını engelleme ve sorulan sınıfı koruma."""

import unittest

from backend.app.config import ContrastiveQuerySettings
from backend.app.models.base_detector import BaseDetector
from backend.app.services.inference_orchestrator import run_detection
from backend.app.utils.contrastive import contrastive_queries, keep_requested


def det(label, left=0, score=0.5):
    return {"label": label, "model_query": label, "confidence": score,
            "box": {"xmin": left, "ymin": 0, "xmax": left + 10, "ymax": 10}}


class ContrastiveQueryTests(unittest.TestCase):
    def test_query_and_related_classes_are_never_distractors(self):
        for query, forbidden in [("dog", {"dog", "cat"}), ("man", {"person"}),
                                 ("coffee cup", {"cup", "bottle"}), ("red car", {"car"}),
                                 ("backpack", {"bag"}), ("face", {"person"})]:
            with self.subTest(query=query):
                extra = contrastive_queries([query])
                self.assertTrue(extra)
                self.assertFalse(forbidden & set(extra), extra)

    def test_disabled_settings_add_nothing(self):
        self.assertEqual(contrastive_queries(["dog"], ContrastiveQuerySettings(enabled=False)), [])

    def test_keep_requested_drops_distractor_labels_and_normalizes(self):
        kept = keep_requested([det("person"), det("t - shirt", 20), det("dog", 40)], ["t-shirt", "dog"])
        self.assertEqual([d["label"] for d in kept], ["t-shirt", "dog"])

    def test_absent_object_is_not_hallucinated_end_to_end(self):
        class Fake(BaseDetector):
            model_id, name, response_model = "grounding-dino", "Fake", "fake"
            use_contrastive_queries = True

            def __init__(self):
                self.calls = []

            def _infer_raw(self, image, queries, threshold):
                return []

            def infer_queries(self, image, queries, threshold, text_threshold=None):
                self.calls.append(list(queries))
                # Tek sorguda adam "dog" olur; karşıt sorguda doğru sınıf "person" kazanır.
                return [det("person" if "person" in queries else "dog")]

        plan = {"original_query": "köpek", "detected_language": "tr", "translated_query": "dog",
                "primary_query": "dog", "fallback_queries": []}
        detector = Fake()
        result = run_detection(detector, None, plan)
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["inventory_summary"], {"dog": 0})
        self.assertIn("person", detector.calls[0])
        self.assertEqual(detector.calls[0][0], "dog")


class GroundingDinoPhraseArgmaxTests(unittest.TestCase):
    def test_each_box_gets_single_best_phrase(self):
        from types import SimpleNamespace
        import torch
        from PIL import Image
        from backend.app.models.grounding_dino_service import GroundingDinoService
        service = GroundingDinoService.__new__(GroundingDinoService)
        # [CLS] jacket . person . t - shirt . [SEP]
        ids = torch.tensor([101, 6598, 1012, 2711, 1012, 1056, 1011, 3797, 1012, 102])
        logits = torch.full((3, 256), -10.0)
        logits[0, 1], logits[0, 3] = 2.0, 1.0   # kutu 0: jacket > person (HF "jacket person" yapardı)
        logits[1, 3] = 3.0                      # kutu 1: person
        logits[2, 6] = -2.0                     # kutu 2: eşik altı
        outputs = SimpleNamespace(logits=logits[None], pred_boxes=torch.tensor([[[0.5, 0.5, 0.2, 0.2]] * 3]))
        with Image.new("RGB", (100, 50)) as image:
            result = service._phrase_argmax(outputs, ids, ["jacket", "person", "t-shirt"], image, 0.3)
        self.assertEqual([d["label"] for d in result], ["jacket", "person"])
        self.assertAlmostEqual(result[0]["confidence"], torch.sigmoid(torch.tensor(2.0)).item(), places=5)
        for key, expected in {"xmin": 40.0, "ymin": 20.0, "xmax": 60.0, "ymax": 30.0}.items():
            self.assertAlmostEqual(result[0]["box"][key], expected, places=4)


if __name__ == "__main__":
    unittest.main()
