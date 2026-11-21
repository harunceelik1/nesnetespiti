import unittest
from unittest.mock import MagicMock, patch


# Bu dosya sorgu aktarımını birebir sınar; karşıt sorgular (test_contrastive.py) kapatılır.
from backend.app.config import ContrastiveQuerySettings as _ContrastiveSettings
_contrastive_patch = patch("backend.app.config.CONTRASTIVE_QUERIES", _ContrastiveSettings(enabled=False))


def setUpModule():
    _contrastive_patch.start()


def tearDownModule():
    _contrastive_patch.stop()


try:
    import torch
    from PIL import Image
    from backend.app.config import GroundingDinoSettings
    from backend.app.services.query_processor import process_query
    from backend.app.models.grounding_dino_service import GroundingDinoService
except ImportError:
    GroundingDinoService = None


@unittest.skipIf(GroundingDinoService is None, "Backend sanal ortamını kullanın.")
class GroundingDinoTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", (100, 80), "white")
        self.translation = MagicMock()
        self.translation.prepare_query.return_value = {
            "original_query": "bag", "primary_query": "bag",
            "detected_language": "en", "translated_query": None,
        }
        self.processor = MagicMock()
        self.inputs = MagicMock()
        self.inputs.to.return_value = {"input_ids": torch.tensor([[1, 2]])}
        self.processor.return_value = self.inputs
        self.processor.post_process_grounded_object_detection.return_value = [{
            "boxes": torch.tensor([[10.0, 20.0, 70.0, 75.0]]),
            "scores": torch.tensor([0.82]),
            "text_labels": ["bag"],
        }]
        self.model = MagicMock()
        self.processor_loader = self.enterContext(patch(
            "backend.app.models.grounding_dino_service.AutoProcessor.from_pretrained",
            return_value=self.processor,
        ))
        self.model_loader = self.enterContext(patch(
            "backend.app.models.grounding_dino_service.AutoModelForZeroShotObjectDetection.from_pretrained",
            return_value=self.model,
        ))

    def tearDown(self):
        self.image.close()

    def make_service(self, cuda=False):
        with patch("backend.app.models.grounding_dino_service.torch.cuda.is_available", return_value=cuda):
            return GroundingDinoService(
                GroundingDinoSettings(box_threshold=0.42, text_threshold=0.27)
            )

    def test_cpu_contract_and_independent_thresholds(self):
        service = self.make_service()
        result = service.detect_result(self.image, process_query("bag", self.translation), threshold=0.99)
        self.assertEqual(result["model"], "grounding-dino")
        self.assertEqual(result["device"], "cpu")
        self.assertGreaterEqual(result["inference_time_ms"], 0)
        self.assertAlmostEqual(result["detections"][0]["confidence"], 0.82, places=5)
        self.assertEqual(result["detections"][0]["box"], {
            "xmin": 10.0, "ymin": 20.0, "xmax": 70.0, "ymax": 75.0,
        })
        args = self.processor.post_process_grounded_object_detection.call_args.kwargs
        self.assertEqual(args["threshold"], 0.42)
        self.assertEqual(args["text_threshold"], 0.27)
        self.assertEqual(args["target_sizes"], [(80, 100)])
        self.assertEqual(self.processor.call_args.kwargs["text"], [["bag"]])

    def test_model_is_loaded_once_across_requests(self):
        service = self.make_service()
        service.detect_result(self.image, process_query("bag", self.translation), 0.2)
        service.detect_result(self.image, process_query("bag", self.translation), 0.3)
        self.processor_loader.assert_called_once()
        self.model_loader.assert_called_once()
        self.assertEqual(self.model.call_count, 2)

    def test_multiple_queries_and_single_string(self):
        service = self.make_service()
        service.detect_queries(self.image, ["bag", "backpack"])
        self.assertEqual(self.processor.call_args.kwargs["text"], [["bag", "backpack"]])
        service.detect_queries(self.image, "bag")
        self.assertEqual(self.processor.call_args.kwargs["text"], [["bag"]])

    def test_cuda_selection_and_synchronized_inference(self):
        service = self.make_service(cuda=True)
        with patch("backend.app.models.grounding_dino_service.torch.cuda.synchronize") as synchronize:
            result = service.detect_queries(self.image, "bag")
        self.assertEqual(result["device"], "cuda")
        self.model.to.assert_called_once_with("cuda")
        self.inputs.to.assert_called_once_with("cuda")
        self.assertEqual(synchronize.call_count, 2)

    def test_config_rejects_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            GroundingDinoSettings(box_threshold=1.1)

    def test_adaptive_box_text_thresholds_reach_processor_without_mutating_config(self):
        service = self.make_service()
        service.detect_result(self.image, process_query("bag", self.translation),
                              threshold=0.30, text_threshold=0.25)
        args = self.processor.post_process_grounded_object_detection.call_args.kwargs
        self.assertEqual(args["threshold"], 0.30)
        self.assertEqual(args["text_threshold"], 0.25)
        self.assertEqual(service.config.box_threshold, 0.42)
        self.assertEqual(service.config.text_threshold, 0.27)
        service.detect_raw(self.image, process_query("bag", self.translation), 0.01)
        args = self.processor.post_process_grounded_object_detection.call_args.kwargs
        self.assertEqual(args["threshold"], 0.42)
        self.assertEqual(args["text_threshold"], 0.27)


if __name__ == "__main__":
    unittest.main()
