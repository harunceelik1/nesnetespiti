import logging
from collections.abc import Callable, Mapping

from .base_detector import BaseDetector, DetectorError
from .grounding_dino_service import GroundingDinoService
from .owlv2_service import Owlv2LargeService
from .owlvit_service import OwlViTService
from .. import config
from .yoloworld_service import YoloWorldService


logger = logging.getLogger(__name__)


class DetectorRegistry:
    # "owlvit" API yuvası: uygulamada OWLv2 large. Grounding DINO ve YOLO-World yalnızca
    # ölçüm betikleri için kayıtlı; uygulama config.APP_MODELS ile yalnızca OWL yuvasını yükler.
    NAMES = {"owlvit": "OWLv2 large" if config.OWL_VERSION == "v2" else "OWL-ViT",
             "grounding-dino": "Grounding DINO", "yolo-world": "YOLO-World"}

    def __init__(
        self,
        factories: Mapping[str, Callable[[], BaseDetector]] | None = None,
        model_ids: tuple[str, ...] | None = None,
    ):
        factories = factories if factories is not None else {
            "owlvit": Owlv2LargeService if config.OWL_VERSION == "v2" else OwlViTService,
            "grounding-dino": GroundingDinoService,
            "yolo-world": YoloWorldService,
        }
        if model_ids is not None:
            factories = {model_id: factories[model_id] for model_id in model_ids}
        # Bu örnekte sunulan modeller (yüklenemeyenler dahil, "available": False).
        self._names = {model_id: self.NAMES[model_id] for model_id in factories}
        self._detectors: dict[str, BaseDetector] = {}
        for model_id, factory in factories.items():
            try:
                self._detectors[model_id] = factory()
            except Exception:
                # Bir model yüklenemese de diğer model ve FastAPI ayakta kalır.
                logger.exception("%s modeli yüklenemedi; bu model kullanılamayacak.", model_id)

    def validate_id(self, model_id: str) -> None:
        if model_id not in self._names:
            raise DetectorError("Geçersiz model. Desteklenen değerler: " + ", ".join(self._names) + ".", 400)

    def get(self, model_id: str) -> BaseDetector:
        self.validate_id(model_id)
        if model_id not in self._detectors:
            raise DetectorError(
                self._names[model_id] + " modeli yüklenemedi veya kullanılamıyor. Backend terminalini ve model dosyalarına erişimi kontrol edin."
            )
        return self._detectors[model_id]

    def list_models(self) -> list[dict]:
        return [
            {"id": model_id, "name": name, "available": model_id in self._detectors}
            for model_id, name in self._names.items()
        ]
