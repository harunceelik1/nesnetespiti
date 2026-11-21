"""Örnekle arama: kullanıcı görselde bir nesneyi kutuyla işaretler, benzerleri bulunur.

Metin sorgusu ve çeviri yoktur; bu yüzden "çikolata ↔ sakız" gibi kelimeyle zor
ayrılan ürünlerde ve sözlükte olmayan nesnelerde kullanılabilir. Yalnızca OWL
yuvası (OWLv2) destekler; DINO ve YOLO-World görsel sorgu almaz.
"""

from time import perf_counter

from .. import config
from ..models.base_detector import DetectorError
from ..services.inventory_service import add_inventory
from ..utils.nms import calculate_containment, calculate_iou

DEFAULT_LABEL = "örnek nesne"


def _suppress(candidates: list[dict], settings: config.ExemplarSearchSettings) -> list[dict]:
    kept = []
    for candidate in sorted(candidates, key=lambda c: -c["confidence"]):
        if any(calculate_iou(candidate["box"], k["box"]) > settings.nms_iou
               or calculate_containment(candidate["box"], k["box"]) > settings.max_containment for k in kept):
            continue
        kept.append(candidate)
    return kept


def validate_box(box: dict, width: int, height: int, settings: config.ExemplarSearchSettings | None = None) -> dict:
    """Kutuyu görsel sınırlarına kırpar; çok küçük ya da ters kutuyu reddeder."""
    settings = settings or config.EXEMPLAR_SEARCH
    clipped = {"xmin": max(0.0, min(box["xmin"], box["xmax"])), "ymin": max(0.0, min(box["ymin"], box["ymax"])),
               "xmax": min(float(width), max(box["xmin"], box["xmax"])), "ymax": min(float(height), max(box["ymin"], box["ymax"]))}
    if clipped["xmax"] - clipped["xmin"] < settings.min_box_side or clipped["ymax"] - clipped["ymin"] < settings.min_box_side:
        raise DetectorError("Örnek kutu çok küçük ya da görselin dışında; nesnenin etrafına daha büyük bir kutu çizin.", 422)
    return clipped


def search_by_example(detector, image, example_box: dict, label: str | None = None,
                      settings: config.ExemplarSearchSettings | None = None) -> dict:
    settings = settings or config.EXEMPLAR_SEARCH
    if not hasattr(detector, "example_candidates"):
        raise DetectorError(f"{detector.name} örnekle aramayı desteklemiyor; OWLv2 kullanın.", 422)
    label = (label or "").strip() or DEFAULT_LABEL
    box = validate_box(example_box, image.width, image.height, settings)
    started = perf_counter()
    candidates, chosen = detector.example_candidates(image, box)
    passed = [c for c in candidates
              if c["similarity"] >= settings.similarity_threshold and c["objectness"] >= settings.min_objectness]
    kept = _suppress(passed, settings)
    detections = [{"label": label, "canonical_query": label, "model_query": "example",
                   "confidence": c["confidence"], "box": c["box"]} for c in kept]
    return add_inventory({
        "model": detector.response_model, "model_id": detector.model_id, "device": detector.device,
        "inference_time_ms": (perf_counter() - started) * 1000,
        "search_mode": "example",
        "query": label, "original_query": label, "detected_language": "example",
        "translated_query": None, "translation_source": None, "primary_query": label,
        "processed_queries": [], "fallback_triggered": False, "fallback_queries_used": [],
        "raw_detection_count": len(passed), "filtered_detection_count": len(detections),
        "adaptive_threshold_used": settings.similarity_threshold,
        "threshold_selection_reason": "example_similarity",
        "example_box": box, "example_model_box": chosen,
        "detections": detections,
    }, [label])
