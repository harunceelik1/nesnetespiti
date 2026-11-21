"""YOLO-World açık sözlük dedektörü (Ultralytics), ortak BaseDetector sözleşmesiyle."""

import logging
from collections.abc import Callable
from pathlib import Path
from threading import Lock

import torch
from PIL import Image

from ..config import YOLO_WORLD, YoloWorldSettings
from .base_detector import BaseDetector, Detection, DetectorError


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_ROOT / ".cache" / "yolo-world"


def yolo_world_weights_cached(config: YoloWorldSettings = YOLO_WORLD) -> bool:
    """Detector ağırlığı ve CLIP metin kodlayıcısı yerelde var mı (indirme yapmaz)."""
    try:
        from ultralytics.utils import WEIGHTS_DIR
    except ImportError:
        return False
    return (CACHE_DIR / config.weights).is_file() and (Path(WEIGHTS_DIR) / "clip" / "ViT-B-32.pt").is_file()


def _default_model_factory(weights_path: str):
    # Ultralytics yalnızca bu model kullanılırken import edilir: paket kurulu değilse
    # registry bu modeli available=false yapar, OWL-ViT ve DINO etkilenmez.
    from ultralytics import YOLOWorld

    return YOLOWorld(weights_path)


class YoloWorldService(BaseDetector):
    """Sorgular CLIP metin gömmesiyle sınıf adı olarak verilir; yeniden eğitim yoktur."""

    model_id = "yolo-world"
    name = "YOLO-World"
    response_model = "yolo-world"
    use_contrastive_queries = True

    def __init__(
        self,
        config: YoloWorldSettings = YOLO_WORLD,
        model_factory: Callable[[str], object] | None = None,
    ):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # set_classes paylaşılan model durumunu değiştirir; sınıf ayarı ve tahmin
        # birlikte kilitlenir, paralel istekler birbirinin sınıflarını görmez.
        self._lock = Lock()
        self._active_classes: tuple[str, ...] | None = None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.weights_path = CACHE_DIR / config.weights
        # Ağırlık yoksa Ultralytics ilk açılışta bu yola indirir; sonraki
        # açılışlarda proje içindeki önbellek kullanılır. Süreç başına bir kez çağrılır.
        factory = model_factory or _default_model_factory
        self.model = factory(str(self.weights_path))
        # CLIP metin kodlayıcısını başlangıçta yükle: ilk kullanıcı isteği beklemesin.
        with self._lock, torch.inference_mode():
            self._set_classes(("object",))

    def _set_classes(self, classes: tuple[str, ...]) -> None:
        """Aynı sınıf listesi için metin gömmesini yeniden hesaplamaz."""
        if classes == self._active_classes:
            return
        names = list(classes)
        world = getattr(self.model, "model", None)
        try:
            # CLIP modelini önbellekte tutarak her sorgu değişiminde yeniden yüklemeyi önle.
            world.set_classes(names, cache_clip_model=True)
            world.names = names
            # Predictor sınıf adlarını kurulumda kopyalar; yeni sınıflar için sıfırlanır.
            self.model.predictor = None
        except (AttributeError, TypeError):
            # Eski/farklı Ultralytics sürümü: resmi genel API'ye dön.
            self.model.set_classes(names)
        self._active_classes = classes

    def _infer_raw(self, image: Image.Image, queries: list[str], threshold: float) -> list[Detection]:
        classes = tuple(dict.fromkeys(query.strip() for query in queries if query.strip()))
        if not classes:
            raise DetectorError("En az bir nesne sorgusu gereklidir.", 422)
        try:
            with self._lock, torch.inference_mode():
                self._set_classes(classes)
                if self.device == "cuda":
                    torch.cuda.synchronize()
                # PIL RGB görüntüsü doğrudan verilir; Ultralytics BGR dönüşümünü kendisi yapar.
                results = self.model.predict(
                    source=image,
                    conf=threshold,
                    iou=self.config.model_nms_iou,
                    max_det=self.config.max_detections,
                    device=self.device,
                    verbose=False,
                )
                if self.device == "cuda":
                    torch.cuda.synchronize()
            boxes = results[0].boxes
            detections = []
            for xyxy, score, class_index in zip(
                boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()
            ):
                # Etiket gönderilen sorgunun kendisidir; fuzzy eşleme yapılmaz.
                label = classes[int(class_index)]
                xmin, ymin, xmax, ymax = (float(value) for value in xyxy)
                detections.append({
                    "label": label,
                    "model_query": label,
                    "confidence": float(score),
                    "box": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
                })
            return detections
        except DetectorError:
            raise
        except Exception as exc:
            logger.exception("YOLO-World inference başarısız.")
            raise DetectorError("YOLO-World görüntüyü işleyemedi. Backend terminalini kontrol edin.") from exc
