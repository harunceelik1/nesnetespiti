import logging
from pathlib import Path
from threading import Lock
from time import perf_counter

import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

from ..config import GROUNDING_DINO, GroundingDinoSettings
from ..utils.contrastive import contrastive_queries, keep_requested
from ..utils.nms import class_aware_nms
from .base_detector import BaseDetector, Detection, DetectorError, DetectorResult


logger = logging.getLogger(__name__)


class GroundingDinoService(BaseDetector):
    model_id = "grounding-dino"
    name = "Grounding DINO"
    response_model = "grounding-dino"
    use_contrastive_queries = True

    def __init__(self, config: GroundingDinoSettings = GROUNDING_DINO):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._lock = Lock()
        cache_dir = Path(__file__).resolve().parents[3] / ".cache" / "grounding-dino"
        # Kurucu registry tarafından süreç başına bir kez çağrılır.
        self.processor = AutoProcessor.from_pretrained(config.model_name, cache_dir=cache_dir)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(config.model_name, cache_dir=cache_dir)
        self.model.to(self.device)
        self.model.eval()

    def _predict_queries(self, image: Image.Image, queries: str | list[str], *, box_threshold: float | None = None, text_threshold: float | None = None, phrase_argmax: bool = False) -> list[Detection]:
        if isinstance(queries, str):
            queries = [queries]
        queries = list(dict.fromkeys(query.strip() for query in queries if query.strip()))
        if not queries:
            raise DetectorError("En az bir nesne sorgusu gereklidir.", 422)
        try:
            with self._lock, torch.inference_mode():
                # Resmi processor tek görüntü için birden fazla İngilizce adayı alır.
                inputs = self.processor(images=image, text=[queries], return_tensors="pt").to(self.device)
                if self.device == "cuda":
                    torch.cuda.synchronize()
                outputs = self.model(**inputs)
                if phrase_argmax and len(queries) > 1:
                    # HF post-process eşiği geçen tokenları birleştirir ("jacket person"),
                    # karşıt sorguda kutu hiçbir sorguya eşlenemez. Her kutu en yüksek
                    # puanlı tek ifadeye atanır.
                    detections = self._phrase_argmax(
                        outputs, inputs["input_ids"][0], queries, image,
                        self.config.box_threshold if box_threshold is None else box_threshold,
                    )
                    if self.device == "cuda":
                        torch.cuda.synchronize()
                    return detections
                # Bu Transformers sürümünde box_threshold argümanının adı threshold.
                # OWL-ViT'ın HTTP threshold değeri burada kullanılmaz.
                result = self.processor.post_process_grounded_object_detection(
                    outputs=outputs,
                    input_ids=inputs["input_ids"],
                    threshold=self.config.box_threshold if box_threshold is None else box_threshold,
                    text_threshold=self.config.text_threshold if text_threshold is None else text_threshold,
                    target_sizes=[(image.height, image.width)],
                )[0]
                if self.device == "cuda":
                    torch.cuda.synchronize()
                detections = []
                for box, label, score in zip(result["boxes"], result["text_labels"], result["scores"]):
                    xmin, ymin, xmax, ymax = box.tolist()
                    detections.append({
                        "label": label,
                        "model_query": label,
                        "confidence": score.item(),
                        "box": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
                    })
                return detections
        except Exception as exc:
            logger.exception("Grounding DINO inference başarısız.")
            raise DetectorError("Grounding DINO görüntüyü işleyemedi. Backend terminalini kontrol edin.") from exc

    @staticmethod
    def _phrase_spans(input_ids: torch.Tensor, phrase_count: int) -> list[list[int]]:
        """Prompt "a. b. c." tokenlarını ifadelere böl; [CLS]/[SEP]/pad ve '.' hariç."""
        separator, special = 1012, {0, 101, 102}
        spans, current = [], []
        for position, token in enumerate(input_ids.tolist()):
            if token == separator:
                if current:
                    spans.append(current)
                current = []
            elif token not in special:
                current.append(position)
        if current:
            spans.append(current)
        if len(spans) != phrase_count:
            raise DetectorError("Grounding DINO prompt'u sorgu ifadelerine ayrılamadı.")
        return spans

    def _phrase_argmax(self, outputs, input_ids, queries: list[str], image: Image.Image, box_threshold: float) -> list[Detection]:
        """Her kutu: ifade skoru = ifade tokenlarının en yüksek olasılığı; en iyi ifade seçilir.

        Text threshold bu yolda kullanılmaz: etiket eşikle değil, ifadeler arası
        yarışla belirlenir. Kutu skoru seçilen ifadenin skorudur.
        """
        spans = self._phrase_spans(input_ids, len(queries))
        probs = outputs.logits[0].sigmoid()
        phrase_scores = torch.stack([probs[:, span].max(dim=1).values for span in spans], dim=1)
        scores, best = phrase_scores.max(dim=1)
        boxes = outputs.pred_boxes[0]
        detections = []
        for index in torch.nonzero(scores > box_threshold).flatten().tolist():
            cx, cy, w, h = boxes[index].tolist()
            label = queries[best[index].item()]
            detections.append({
                "label": label,
                "model_query": label,
                "confidence": scores[index].item(),
                "box": {"xmin": (cx - w / 2) * image.width, "ymin": (cy - h / 2) * image.height,
                        "xmax": (cx + w / 2) * image.width, "ymax": (cy + h / 2) * image.height},
            })
        return detections

    def _infer_requested(self, image: Image.Image, queries: list[str], threshold: float, text_threshold: float | None) -> list[Detection]:
        """Karşıt sorguda her kutu tek ifadeye atanır; sonra yalnızca sorulanlar tutulur."""
        extra = contrastive_queries(queries) if self.use_contrastive_queries else []
        if not extra:
            return super()._infer_requested(image, queries, threshold, text_threshold)
        # Raw debug akışı (text_threshold=None) HTTP eşiği yerine config box eşiğini kullanır.
        box_threshold = threshold if text_threshold is not None else None
        detections = self._predict_queries(image, [*queries, *extra], box_threshold=box_threshold, phrase_argmax=True)
        return keep_requested(detections, queries)

    def _infer_raw(self, image: Image.Image, queries: list[str], threshold: float) -> list[Detection]:
        return self._predict_queries(image, queries)

    def infer_queries(self, image: Image.Image, queries: list[str], threshold: float, text_threshold: float | None = None) -> list[Detection]:
        # Sadece orchestration açıkça box/text ayarı verirse override uygula.
        # Shared model/config mutate edilmez; paralel istekler eşikleri paylaşmaz.
        if text_threshold is None:
            return self._infer_raw(image, queries, threshold)
        return self._predict_queries(image, queries, box_threshold=threshold, text_threshold=text_threshold)

    def detect_queries(self, image: Image.Image, queries: str | list[str]) -> DetectorResult:
        """Çevrilmiş tek/çoklu İngilizce sorgu için model seviyesi ortak sözleşme."""
        started = perf_counter()
        raw = self._predict_queries(image, queries)
        elapsed_ms = (perf_counter() - started) * 1000
        detections = class_aware_nms(raw)
        return {
            "model": self.response_model, "model_id": self.model_id, "device": self.device,
            "detections": detections, "inference_time_ms": elapsed_ms,
            "raw_detection_count": len(raw), "filtered_detection_count": len(detections),
        }
