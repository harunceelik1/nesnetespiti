"""Model indirmeden gerçek servis akışını sahte inference çıktılarıyla doğrular."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.query_processor import process_query


# Bu dosya sorgu aktarımını birebir sınar; karşıt sorgular (test_contrastive.py) kapatılır.
from backend.app.config import ContrastiveQuerySettings as _ContrastiveSettings
_contrastive_patch = patch("backend.app.config.CONTRASTIVE_QUERIES", _ContrastiveSettings(enabled=False))


def setUpModule():
    _contrastive_patch.start()


def tearDownModule():
    _contrastive_patch.stop()



class QueryFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "app" / "models" / "owlvit_service.py"
        spec = importlib.util.spec_from_file_location(
            "backend.app.models._owlvit_service_test", path
        )
        module = importlib.util.module_from_spec(spec)
        # Yalnızca model bağımlılıklarını taklit et; query processor ve NMS gerçektir.
        with patch.dict(sys.modules, {name: MagicMock() for name in ("torch", "PIL", "transformers")}):
            spec.loader.exec_module(module)
        cls.service_class = module.OwlViTService

    def setUp(self):
        # Model kurucusunu çağırmadan isteklerin akışını test et.
        self.service = self.service_class.__new__(self.service_class)
        self.translation = MagicMock()
        def prepare_query(query):
            english = {"çanta": "bag", "laptop çantası": "laptop bag", "araba": "car"}[query]
            return {"original_query": query, "detected_language": "tr",
                    "translated_query": english, "primary_query": english}
        self.translation.prepare_query.side_effect = prepare_query

    def plan(self, query):
        return process_query(query, self.translation)

    @staticmethod
    def detection(model_query="bag", confidence=0.9):
        return {
            "label": "çanta", "model_query": model_query, "confidence": confidence,
            "box": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100},
        }

    def test_primary_success_does_not_run_fallback(self):
        self.service._infer_raw = MagicMock(return_value=[self.detection()])
        result = self.service.detect_result(None, self.plan("çanta"), 0.2)
        self.assertEqual(self.service._infer_raw.call_count, 1)
        self.assertEqual(self.service._infer_raw.call_args.args[1], ["bag"])
        self.assertEqual(result["primary_query"], "bag")
        self.assertEqual(result["detected_language"], "tr")
        self.assertEqual(result["translated_query"], "bag")
        self.assertEqual(result["processed_queries"], ["bag"])
        self.assertEqual(result["fallback_queries_used"], [])
        self.assertFalse(result["fallback_triggered"])

    def test_empty_primary_runs_fallback_and_cross_query_nms(self):
        raw = [self.detection("handbag", 0.9), self.detection("backpack", 0.8)]
        self.service._infer_raw = MagicMock(side_effect=[[], raw])
        result = self.service.detect_result(None, self.plan("çanta"), 0.37)
        self.assertEqual(self.service._infer_raw.call_count, 2)
        calls = self.service._infer_raw.call_args_list
        self.assertEqual(calls[0].args[1], ["bag"])
        self.assertEqual(calls[1].args[1], ["handbag", "backpack", "tote bag"])
        self.assertTrue(all(call.args[2] == 0.37 for call in calls))
        self.assertTrue(result["fallback_triggered"])
        self.assertEqual(result["fallback_queries_used"], ["handbag", "backpack", "tote bag"])
        self.assertEqual(result["processed_queries"], ["bag", "handbag", "backpack", "tote bag"])
        self.assertEqual(result["raw_detection_count"], 2)
        self.assertEqual(result["filtered_detection_count"], 1)
        self.assertEqual(result["detections"], [raw[0]])

    def test_specific_query_uses_only_specific_fallback(self):
        self.service._infer_raw = MagicMock(side_effect=[[], []])
        result = self.service.detect_result(None, self.plan("laptop çantası"), 0.2)
        self.assertEqual(result["primary_query"], "laptop bag")
        self.assertEqual(result["fallback_queries_used"], ["computer bag", "laptop case"])
        self.assertTrue(result["fallback_triggered"])
        self.assertEqual(result["detections"], [])
        self.assertEqual(result["raw_detection_count"], 0)

    def test_no_fallback_plan_does_not_retry(self):
        self.service._infer_raw = MagicMock(return_value=[])
        result = self.service.detect_result(None, self.plan("araba"), 0.2)
        self.assertEqual(self.service._infer_raw.call_count, 1)
        self.assertFalse(result["fallback_triggered"])
        self.assertEqual(result["processed_queries"], ["car"])

    def test_raw_debug_keeps_all_fallback_boxes(self):
        raw = [self.detection("handbag"), self.detection("backpack", 0.8)]
        self.service._infer_raw = MagicMock(side_effect=[[], raw])
        self.assertEqual(self.service.detect_raw(None, self.plan("çanta"), 0.2), raw)

    def test_existing_service_interfaces_are_preserved(self):
        self.service._infer_raw = MagicMock(return_value=[self.detection()])
        detections, raw_count = self.service.detect_with_counts(None, self.plan("çanta"), 0.2)
        self.assertEqual(raw_count, 1)
        self.assertEqual(self.service.detect(None, self.plan("çanta"), 0.2), detections)


if __name__ == "__main__":
    unittest.main()
