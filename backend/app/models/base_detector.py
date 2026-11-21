from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import TYPE_CHECKING, NotRequired, TypedDict

from ..services.query_processor import ProcessedQuery
from ..utils.contrastive import contrastive_queries, keep_requested
from ..utils.nms import class_aware_nms

if TYPE_CHECKING:
    from PIL import Image


class BoundingBox(TypedDict):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class Detection(TypedDict):
    label: str
    confidence: float
    box: BoundingBox
    model_query: NotRequired[str]
    canonical_query: NotRequired[str]


class DetectorResult(TypedDict):
    model: str
    model_id: str
    detections: list[Detection]
    inference_time_ms: float
    device: str
    original_query: NotRequired[str]
    detected_language: NotRequired[str]
    translated_query: NotRequired[str | None]
    translation_source: NotRequired[str | None]
    primary_query: NotRequired[str]
    processed_queries: NotRequired[list[str]]
    fallback_queries_used: NotRequired[list[str]]
    fallback_triggered: NotRequired[bool]
    raw_detection_count: NotRequired[int]
    filtered_detection_count: NotRequired[int]
    adaptive_threshold_used: NotRequired[float]
    threshold_attempts: NotRequired[list[dict]]
    threshold_selection_reason: NotRequired[str]
    inventory_summary: NotRequired[dict[str, int]]
    total_detected_objects: NotRequired[int]
    processed_query_items: NotRequired[list[dict]]
    adaptive_thresholds_by_query: NotRequired[dict[str, float]]
    query_inference_strategy: NotRequired[str]


class DetectorError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class BaseDetector(ABC):
    """Hazır İngilizce sorgularla ortak fallback/NMS akışı; çeviri yapmaz."""

    model_id: str
    name: str
    response_model: str
    device: str = "cpu"
    # Gerçek servislerde True: sorguya karşıt sınıflar eklenir, yalnızca sorulan
    # etiketler tutulur (bkz. utils/contrastive.py). Test sahteleri etkilenmez.
    use_contrastive_queries: bool = False
    # config.ADAPTIVE_THRESHOLDS anahtarı; None ise model_id kullanılır. Aynı API
    # yuvasındaki farklı modeller (OWL-ViT v1 / OWLv2) ayrı skor ölçeği taşır.
    policy_key: str | None = None

    def detect(self, image: Image.Image, query: ProcessedQuery, threshold: float) -> list[Detection]:
        detections, _ = self.detect_with_counts(image, query, threshold)
        return detections

    def detect_with_counts(self, image: Image.Image, query: ProcessedQuery, threshold: float) -> tuple[list[Detection], int]:
        result = self.detect_result(image, query, threshold)
        return result["detections"], result["raw_detection_count"]

    def detect_result(self, image: Image.Image, query: ProcessedQuery, threshold: float, *, text_threshold: float | None = None, inference_queries: list[str] | None = None) -> DetectorResult:
        result = self._detect_raw_result(image, query, threshold, text_threshold=text_threshold, inference_queries=inference_queries)
        # Mevcut class-aware IoU NMS (0.60) ve devre dışı custom filtreler korunur.
        detections = class_aware_nms(result["detections"])
        return {**result, "detections": detections, "filtered_detection_count": len(detections)}

    def detect_raw(self, image: Image.Image, query: ProcessedQuery, threshold: float) -> list[Detection]:
        # Debug akışı NMS uygulamaz.
        return self._detect_raw_result(image, query, threshold)["detections"]

    def infer_queries(self, image: Image.Image, queries: list[str], threshold: float, text_threshold: float | None = None) -> list[Detection]:
        """Orchestration için eşik sözleşmesi; varsayılan detector tek eşik kullanır."""
        return self._infer_raw(image, queries, threshold)

    def _detect_raw_result(self, image: Image.Image, query: ProcessedQuery, threshold: float, *, text_threshold: float | None = None, inference_queries: list[str] | None = None) -> DetectorResult:
        plan = query
        # Orchestrator fallback fazında adayları açıkça verir; primary metadata
        # değişmez. Eski doğrudan servis/raw çağrılarının davranışı korunur.
        active_queries = inference_queries if inference_queries is not None else [plan["primary_query"]]
        processed_queries = [plan["primary_query"]]
        # Çeviri ve model yükleme hariç; detector ön/son işlemleri ve gerekirse
        # fallback inference dahil toplam süre. NMS bu ölçümden sonra uygulanır.
        started = perf_counter()
        detections = self._infer_requested(image, active_queries, threshold, text_threshold)
        fallback_queries_used = list(active_queries) if inference_queries is not None else []
        if not detections and inference_queries is None and plan["fallback_queries"]:
            fallback_queries_used = plan["fallback_queries"]
            detections = self._infer_requested(
                image,
                fallback_queries_used,
                threshold,
                text_threshold,
            )
        processed_queries = processed_queries + fallback_queries_used
        elapsed_ms = (perf_counter() - started) * 1000
        # Orijinal metin yalnızca gösterim içindir; model input'una asla eklenmez.
        display_label = " ".join(plan["original_query"].split())
        detections = [{**detection, "label": display_label} for detection in detections]
        return {
            "model": self.response_model,
            "model_id": self.model_id,
            "device": self.device,
            "inference_time_ms": elapsed_ms,
            "original_query": plan["original_query"],
            "detected_language": plan["detected_language"],
            "translated_query": plan["translated_query"],
            # lexicon / model / user / None (İngilizce sorgu): arayüz "Aranan ifade" için kullanır.
            "translation_source": plan.get("translation_source"),
            "primary_query": plan["primary_query"],
            "processed_queries": processed_queries,
            "fallback_queries_used": fallback_queries_used,
            "fallback_triggered": bool(fallback_queries_used),
            "detections": detections,
            "raw_detection_count": len(detections),
        }

    def _infer_requested(self, image: Image.Image, queries: list[str], threshold: float, text_threshold: float | None) -> list[Detection]:
        """Karşıt sorgular açıksa onlarla birlikte çalıştır, yalnızca sorulanları döndür."""
        extra = contrastive_queries(queries) if self.use_contrastive_queries else []
        if not extra:
            return self.infer_queries(image, queries, threshold, text_threshold)
        detections = self.infer_queries(image, [*queries, *extra], threshold, text_threshold)
        return keep_requested(detections, queries)

    @abstractmethod
    def _infer_raw(self, image: Image.Image, queries: list[str], threshold: float) -> list[Detection]:
        """Hazırlanmış İngilizce sorgular için modelin threshold sonrası kutuları."""
        raise NotImplementedError
