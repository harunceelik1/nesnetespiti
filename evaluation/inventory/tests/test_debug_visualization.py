"""Debug çizimi: sentetik kutular, fake detector, ağ/model yükleme yok."""

import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from evaluation.inventory import evaluate_inventory as evaluation
from evaluation.inventory.debug_visualization import render_debug_image
from evaluation.inventory.tests.test_evaluate_inventory import FakeDetector, annotation


class DebugVisualizationTests(unittest.TestCase):
    def test_two_panels_show_gt_labels_and_prediction_confidence_without_mutation(self):
        gt = annotation()["objects"]
        predictions = FakeDetector("owlvit").infer_queries(None, [], 0.05, None)
        before = copy.deepcopy((gt, predictions))
        with Image.new("RGB", (100, 80), "white") as image:
            pixels = image.tobytes()
            with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as text:
                with render_debug_image(image, gt, predictions, model="owlvit", image_id="fixed-id") as result:
                    self.assertGreater(result.width, 2 * image.width)
                    self.assertGreater(result.height, image.height)
                labels = [call.args[2] for call in text.call_args_list]
                self.assertIn("milk", labels)
                self.assertIn("milk: 0.900", labels)
                self.assertIn("candy: 0.700", labels)
                self.assertIn("GROUND TRUTH (2)", labels)
                self.assertIn("PREDICTIONS - owlvit (3)", labels)
            self.assertEqual(image.tobytes(), pixels)
        self.assertEqual((gt, predictions), before)

    def test_debug_reuses_evaluated_predictions_and_does_not_change_metrics_or_reports(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            (data / "calibration/images").mkdir(parents=True)
            image_path = data / "calibration/images/cal-a.jpg"
            with Image.new("RGB", (24, 24), "white") as image:
                image.save(image_path)
            original = image_path.read_bytes()
            detector = FakeDetector("owlvit")
            result = evaluation.evaluate_model(detector, [annotation()], 0.5, data)
            before = copy.deepcopy(result)
            paths = evaluation.save_results(result, "owlvit", {}, root / "results")
            reports = {path: path.read_bytes() for path in paths}
            with patch.object(evaluation, "infer_categories", side_effect=AssertionError("No additional inference")):
                files = evaluation.save_debug_images(result, [annotation()], paths[0], data)
            self.assertEqual(len(detector.calls), 1)
            self.assertEqual(result, before)
            self.assertEqual(image_path.read_bytes(), original)
            self.assertEqual({path: path.read_bytes() for path in paths}, reports)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].parent, root / "results/debug")
            self.assertIn(paths[0].stem, files[0].name)
            self.assertIn("cal-a", files[0].name)
            with Image.open(files[0]) as image:
                self.assertEqual(image.format, "PNG")
            self.assertEqual(json.loads(paths[0].read_text())["summary"], result["summary"])

    def test_cli_debug_is_opt_in_and_dry_run_never_saves_images(self):
        for flags, expected in [([], 0), (["--save-debug-images"], 1), (["--save-debug-images", "--dry-run"], 0)]:
            with self.subTest(flags=flags), redirect_stdout(StringIO()), \
                    patch.object(evaluation, "load_calibration", return_value=([annotation()], {})), \
                    patch.object(evaluation, "make_detector"), \
                    patch.object(evaluation, "evaluate_model", return_value={"summary": {}}), \
                    patch.object(evaluation, "save_results", return_value=(Path("report.json"), Path("report.csv"))), \
                    patch.object(evaluation, "save_debug_images", return_value=[]) as debug:
                self.assertEqual(evaluation.main(["--limit", "1", *flags]), 0)
                self.assertEqual(debug.call_count, expected)


if __name__ == "__main__":
    unittest.main()
