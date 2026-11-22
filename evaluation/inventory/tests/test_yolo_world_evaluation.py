"""YOLO-World evaluation bağlantısı; model yüklenmez, ağ erişimi yapılmaz."""

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from evaluation.inventory import evaluate_inventory as evaluation
from evaluation.inventory.tests.test_evaluate_inventory import annotation


class YoloWorldEvaluationTests(unittest.TestCase):
    def test_fixed_baseline_threshold_comes_from_production_config(self):
        settings = evaluation.threshold_settings("yolo-world")
        from backend.app.config import ADAPTIVE_THRESHOLDS
        self.assertEqual(settings, {"strategy": "fixed_smoke_baseline",
                                    "confidence_threshold": ADAPTIVE_THRESHOLDS["yolo-world"].thresholds[0]})

    def test_all_runs_three_models_and_both_is_unchanged(self):
        self.assertEqual(evaluation.MODEL_GROUPS["both"], ("owlvit", "grounding-dino"))
        output = StringIO()
        with patch.object(evaluation, "load_calibration", return_value=([annotation()], {})), \
                patch.object(evaluation, "make_detector", side_effect=AssertionError("No models")) as factory:
            with redirect_stdout(output):
                self.assertEqual(evaluation.main(["--dry-run", "--model", "all", "--limit", "1"]), 0)
        factory.assert_not_called()
        plan = json.loads(output.getvalue())
        self.assertEqual(list(plan["model_thresholds"]), ["owlvit", "grounding-dino", "yolo-world"])
        self.assertEqual(plan["max_forward_calls"], 3)

    def test_missing_cached_weights_refuse_instead_of_downloading(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("Backend sanal ortamını kullanın.")
        with patch("backend.app.models.yoloworld_service.yolo_world_weights_cached", return_value=False), \
                patch("backend.app.models.yoloworld_service.YoloWorldService") as service:
            with self.assertRaises(FileNotFoundError):
                evaluation.make_detector("yolo-world")
        service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
