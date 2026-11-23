"""Uygulama tek yöntemle çalışır: OWLv2 large ("owlvit" yuvası). Diğer modeller yalnızca ölçüm içindir."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app import config, main
from backend.app.models.base_detector import DetectorError
from backend.app.models.detector_registry import DetectorRegistry
from backend.app.models.owlv2_service import Owlv2LargeService, Owlv2Service
from backend.app.services import sensitivity


class SingleModelTests(unittest.TestCase):
    def test_owl_slot_is_owlv2_large_with_its_own_thresholds(self):
        self.assertEqual(Owlv2LargeService.model_name, "google/owlv2-large-patch14-ensemble")
        self.assertEqual(Owlv2LargeService.model_id, "owlvit")
        self.assertEqual(Owlv2LargeService.policy_key, "owlv2-large")
        # Base modelin eşikleri large için kalibre değil; ayrı anahtar kullanılmalı.
        self.assertNotEqual(Owlv2LargeService.policy_key, Owlv2Service.policy_key)
        self.assertIn("owlv2-large", config.ADAPTIVE_THRESHOLDS)
        self.assertIn("owlv2-large", config.SENSITIVITY_THRESHOLDS)
        self.assertEqual(DetectorRegistry.NAMES["owlvit"], "OWLv2 large")

    def test_policy_for_large_reads_large_thresholds(self):
        detector = Owlv2LargeService.__new__(Owlv2LargeService)  # ağırlık yüklenmez
        self.assertIs(sensitivity.detection_policy(detector, "balanced"), config.ADAPTIVE_THRESHOLDS["owlv2-large"])
        for level in ("strict", "loose"):
            self.assertEqual(sensitivity.detection_policy(detector, level).thresholds,
                             (config.SENSITIVITY_THRESHOLDS["owlv2-large"][level],))

    def test_registry_model_ids_limits_loaded_and_accepted_models(self):
        owl, dino = MagicMock(), MagicMock()
        registry = DetectorRegistry({"owlvit": owl, "grounding-dino": dino}, model_ids=("owlvit",))
        owl.assert_called_once()
        dino.assert_not_called()
        self.assertEqual(registry.list_models(), [{"id": "owlvit", "name": "OWLv2 large", "available": True}])
        registry.validate_id("owlvit")
        with self.assertRaises(DetectorError) as error:
            registry.validate_id("grounding-dino")
        self.assertEqual(error.exception.status_code, 400)

    def test_app_loads_only_the_owl_slot(self):
        self.assertEqual(config.APP_MODELS, ("owlvit",))
        with patch.object(main, "TranslationService"), \
                patch.object(main, "DetectorRegistry") as registry_class:
            with TestClient(main.app):
                pass
        registry_class.assert_called_once_with(model_ids=("owlvit",))


if __name__ == "__main__":
    unittest.main()
