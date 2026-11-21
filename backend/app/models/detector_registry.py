import logging
from collections.abc import Callable, Mapping

from .base_detector import BaseDetector, DetectorError
from .grounding_dino_service import GroundingDinoService
from .owlv2_service import Owlv2Service
from .owlvit_service import OwlViTService
from .. import config
from .yoloworld_service import YoloWorldService


logger = logging.getLogger(__name__)


class DetectorRegistry:
    NAMES = {"owlvit": "OWLv2" if config.OWL_VERSION == "v2" else "OWL-ViT",
             "grounding-dino": "Grounding DINO", "yolo-world": "YOLO-World"}

    def __init__(
        self,
        factories: Mapping[str, Callable[[], BaseDetector]] | None = None,
    ):
        factories = factories if factories is not None else {
            "owlvit": Owlv2Service if config.OWL_VERSION == "v2" else OwlViTService,
            "grounding-dino": GroundingDinoService,
            "yolo-world": YoloWorldService,
        }
        self._detectors: dict[str, BaseDetector] = {}
        for model_id, factory in factories.items():
            try:
                self._detectors[model_id] = factory()
            except Exception:
                # Bir model yüklenemese de diğer model ve FastAPI ayakta kalır.
                logger.exception("%s modeli yüklenemedi; bu model kullanılamayacak.", model_id)

    @classmethod
    def validate_id(cls, model_id: str) -> None:
        if model_id not in cls.NAMES:
            raise DetectorError("Geçersiz model. Desteklenen değerler: " + ", ".join(cls.NAMES) + ".", 400)

    def get(self, model_id: str) -> BaseDetector:
        self.validate_id(model_id)
        if model_id not in self._detectors:
            raise DetectorError(
                self.NAMES[model_id] + " modeli yüklenemedi veya kullanılamıyor. Backend terminalini ve model dosyalarına erişimi kontrol edin."
            )
        return self._detectors[model_id]

    def list_models(self) -> list[dict]:
        return [
            {"id": model_id, "name": name, "available": model_id in self._detectors}
            for model_id, name in self.NAMES.items()
        ]
