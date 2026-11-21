"""Örnekle arama: süzgeç, kutu doğrulama ve /detect-by-example ucu (model sahte)."""

from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch

import torch
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import main
from backend.app.models.base_detector import BaseDetector, DetectorError
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.models.owlvit_service import OwlViTService
from backend.app.services.exemplar_search import search_by_example, validate_box


def box(x1, y1, x2, y2):
    return {"xmin": x1, "ymin": y1, "xmax": x2, "ymax": y2}


def candidate(similarity, objectness, b):
    return {"confidence": similarity, "similarity": similarity, "objectness": objectness, "box": b}


class FakeOwl:
    model_id, name, response_model, device = "owlvit", "OWLv2", "OWLv2", "cpu"

    def __init__(self, candidates):
        self.candidates, self.calls = candidates, []

    def example_candidates(self, image, example_box):
        self.calls.append(example_box)
        return self.candidates, example_box


class ExemplarFilterTests(unittest.TestCase):
    image = Image.new("RGB", (200, 100))

    def test_keeps_similar_objects_and_drops_weak_or_background(self):
        detector = FakeOwl([
            candidate(1.00, 0.9, box(10, 10, 40, 40)),   # örneğin kendisi
            candidate(0.93, 0.8, box(100, 10, 130, 40)),  # benzer ürün
            candidate(0.95, 0.01, box(150, 10, 180, 40)), # objectness düşük: boşluk/parça
            candidate(0.70, 0.9, box(60, 60, 90, 90)),    # farklı ürün
        ])
        result = search_by_example(detector, self.image, box(10, 10, 40, 40), "çikolata")
        self.assertEqual([d["box"]["xmin"] for d in result["detections"]], [10, 100])
        self.assertEqual(result["inventory_summary"], {"çikolata": 2})
        self.assertEqual(result["search_mode"], "example")
        self.assertEqual(result["model_id"], "owlvit")

    def test_part_box_inside_kept_box_is_suppressed(self):
        detector = FakeOwl([candidate(0.99, 0.9, box(10, 10, 60, 60)),
                            candidate(0.95, 0.9, box(15, 15, 35, 35))])  # iç parça, IoU düşük
        result = search_by_example(detector, self.image, box(10, 10, 60, 60))
        self.assertEqual(len(result["detections"]), 1)
        self.assertEqual(result["detections"][0]["label"], "örnek nesne")

    def test_box_is_clipped_and_tiny_box_rejected(self):
        self.assertEqual(validate_box(box(150, -5, 250, 50), 200, 100), box(150, 0, 200, 50))
        self.assertEqual(validate_box(box(40, 40, 10, 10), 200, 100), box(10, 10, 40, 40))
        with self.assertRaises(DetectorError) as error:
            validate_box(box(10, 10, 13, 60), 200, 100)
        self.assertEqual(error.exception.status_code, 422)

    def test_text_only_detector_is_rejected(self):
        detector = MagicMock(spec=BaseDetector)
        detector.name = "Grounding DINO"
        with self.assertRaises(DetectorError):
            search_by_example(detector, self.image, box(10, 10, 40, 40))


class TinyOwlModel:
    """OWL arayüzünü taklit eder: 3 kutu, 2'si aynı gömüye sahip."""

    def image_embedder(self, pixel_values):
        return (torch.zeros(1, 1, 3, 4),)

    def box_predictor(self, feats, feature_map):
        # cx, cy, w, h (0-1); görsel 100x100 → kutular 10-30, 60-80 ve 40-60.
        return torch.tensor([[[0.2, 0.2, 0.2, 0.2], [0.7, 0.7, 0.2, 0.2], [0.5, 0.5, 0.2, 0.2]]])

    def class_predictor(self, feats):
        return None, torch.tensor([[[1.0, 0, 0, 0], [1.0, 0, 0, 0], [0, 1.0, 0, 0]]])

    def objectness_predictor(self, feats):
        return torch.tensor([[2.0, 2.0, 2.0]])


class ExampleCandidatesTests(unittest.TestCase):
    def test_similarity_comes_from_box_under_drawn_region(self):
        service = OwlViTService.__new__(OwlViTService)
        service.processor = MagicMock(return_value={"pixel_values": torch.zeros(1, 3, 4, 4)})
        service.model, service.device = TinyOwlModel(), "cpu"
        candidates, chosen = service.example_candidates(Image.new("RGB", (100, 100)), box(9, 9, 31, 31))
        self.assertAlmostEqual(chosen["xmin"], 10, places=3)
        self.assertEqual([round(c["similarity"], 3) for c in candidates], [1.0, 1.0, 0.0])
        self.assertAlmostEqual(candidates[1]["box"]["xmin"], 60, places=3)


class ExampleEndpointTests(unittest.TestCase):
    def test_endpoint_returns_detections_and_image(self):
        fake = FakeOwl([candidate(0.99, 0.9, box(2, 2, 12, 12))])
        registry = DetectorRegistry({"owlvit": lambda: fake})
        buffer = BytesIO()
        Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
        with patch.object(main, "TranslationService", return_value=MagicMock()), \
                patch.object(main, "DetectorRegistry", return_value=registry), TestClient(main.app) as client:
            response = client.post("/detect-by-example", data={
                "xmin": "1", "ymin": "1", "xmax": "14", "ymax": "14", "label": "kalem", "include_image": "true"},
                files={"image": ("t.png", buffer.getvalue(), "image/png")})
            tiny = client.post("/detect-by-example", data={"xmin": "1", "ymin": "1", "xmax": "3", "ymax": "3"},
                               files={"image": ("t.png", buffer.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["inventory_summary"], {"kalem": 1})
        self.assertEqual(body["annotated_image"]["media_type"], "image/jpeg")
        self.assertEqual(fake.calls[0], box(1, 1, 14, 14))
        self.assertEqual(tiny.status_code, 422)


if __name__ == "__main__":
    unittest.main()
