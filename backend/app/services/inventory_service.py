"""İstek içi multi-query orchestration; model örnekleri ve config mutate edilmez."""

from time import perf_counter

from ..models.base_detector import BaseDetector, DetectorError
from ..utils.contrastive import contrastive_queries
from ..utils.nms import class_aware_nms


def add_inventory(result: dict, primary_queries: list[str]) -> dict:
    counts = dict.fromkeys(primary_queries, 0)
    for detection in result["detections"]:
        canonical = detection["canonical_query"]
        counts[canonical] += 1
    return {**result, "inventory_summary": counts,
            "total_detected_objects": len(result["detections"])}


class _SharedOwlPrimary(BaseDetector):
    """Aynı image/eşik primary forward'unu sadece bu HTTP isteği içinde paylaş."""

    def __init__(self, detector, primaries):
        self.detector, self.primaries, self.cache = detector, primaries, {}
        self.model_id, self.name = detector.model_id, detector.name
        self.response_model, self.device = detector.response_model, detector.device
        self.policy_key = getattr(detector, "policy_key", None)
        self.use_contrastive_queries = detector.use_contrastive_queries
        # Tek forward: tüm primary'ler + ortak karşıt sınıflar. Primary'ler zaten
        # birbirinin karşıtıdır; karşıtlar primary'lerle ilişkiliyse çıkarılır.
        self.extra = contrastive_queries(primaries) if self.use_contrastive_queries else []

    def infer_queries(self, image, queries, threshold, text_threshold=None):
        requested = [q for q in queries if q in self.primaries]
        if len(requested) != 1 or queries[0] != requested[0]:
            return self.detector.infer_queries(image, queries, threshold, text_threshold)
        key = (threshold, text_threshold)
        if key not in self.cache:
            raw = self.detector.infer_queries(image, [*self.primaries, *self.extra], threshold, text_threshold)
            # OWL-ViT candidate etiketi tam eşleşir; bilinmeyen etiketi yanlış
            # envanter sınıfına atamak yerine anlaşılır hata üret.
            if any(d["label"] not in self.primaries and d["label"] not in self.extra for d in raw):
                raise DetectorError("Model çıktısı istenen nesne sorgularıyla eşleştirilemedi.")
            self.cache[key] = raw
        return [dict(d) for d in self.cache[key] if d["label"] == requested[0]]

    def _infer_raw(self, image, queries, threshold):
        return self.infer_queries(image, queries, threshold)


def run_inventory_detection(detector, image, query, policy, run_single):
    started = perf_counter()
    items = query["processed_query_items"]
    primaries = [item["primary_query"] for item in items]
    # DINO'nun decoded phrase'leri çoklu prompt'ta birleştirilebildiği için
    # production envanter ataması bağımsız sorgularla kesin tutulur.
    active_detector = _SharedOwlPrimary(detector, primaries) if detector.model_id == "owlvit" and len(items) > 1 else detector
    results = [run_single(active_detector, image, item, policy) for item in items]
    detections = [d for result in results for d in result["detections"]]
    # Display label'dan bağımsız canonical sınıfta NMS; farklı sınıflar korunur.
    canonical = class_aware_nms([{**d, "label": d["canonical_query"]} for d in detections])
    display_labels = {item["primary_query"]: " ".join(item["original_query"].split()) for item in items}
    final = [{**d, "label": display_labels[d["canonical_query"]]} for d in canonical]
    processed_items = [{**item, **{key: result[key] for key in (
        "processed_queries", "fallback_triggered", "fallback_queries_used", "raw_detection_count",
        "filtered_detection_count", "adaptive_threshold_used", "threshold_attempts", "threshold_selection_reason",
        "inference_time_ms")}} for item, result in zip(items, results)]
    response = {
        "model": detector.response_model, "model_id": detector.model_id, "device": detector.device,
        "original_query": query["original_query"], "detected_language": query["detected_language"],
        "translated_query": query["translated_query"], "primary_query": query["primary_query"],
        "processed_queries": list(dict.fromkeys(q for result in results for q in result["processed_queries"])),
        "processed_query_items": processed_items,
        "fallback_triggered": any(r["fallback_triggered"] for r in results),
        "fallback_queries_used": list(dict.fromkeys(q for r in results for q in r["fallback_queries_used"])),
        "detections": final, "raw_detection_count": sum(r["raw_detection_count"] for r in results),
        "filtered_detection_count": len(final),
        "threshold_attempts": [{**attempt, "canonical_query": item["primary_query"]}
                               for item, result in zip(items, results) for attempt in result["threshold_attempts"]],
        "threshold_selection_reason": "per_query_adaptive_threshold",
        "adaptive_thresholds_by_query": {p: r["adaptive_threshold_used"] for p, r in zip(primaries, results)},
        "inference_time_ms": (perf_counter() - started) * 1000,
        "query_inference_strategy": "shared_owlvit_primary" if active_detector is not detector else "independent_queries",
    }
    thresholds = {r["adaptive_threshold_used"] for r in results}
    if len(thresholds) == 1:
        response["adaptive_threshold_used"] = next(iter(thresholds))
    return add_inventory(response, primaries)


def detect_raw_queries(detector, image, query, threshold):
    """Raw debug endpoint'i adaptive/NMS eklemeden her planı ayrı çalıştırır."""
    items = query.get("processed_query_items", [query])
    return [{**d, "canonical_query": item["primary_query"]}
            for item in items for d in detector.detect_raw(image, item, threshold)]
