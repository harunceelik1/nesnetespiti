"""Modelden bağımsız, sınırlı ve açıklanabilir adaptive eşik seçimi."""

from math import isfinite
from time import perf_counter

from .. import config
from ..config import ADAPTIVE_THRESHOLDS, AdaptiveThresholdSettings
from ..models.base_detector import BaseDetector, DetectorResult
from ..utils.scene_box_filter import apply_scene_box_filter, attach_scene_box_diagnostics
from .query_processor import ProcessedQuery


def evaluate_result(result: DetectorResult, threshold: float, policy: AdaptiveThresholdSettings) -> dict:
    """Raw yükü, mevcut NMS çıktısı ve modelin kendi skor ölçeğini değerlendir."""
    detections = result["detections"]
    scores = [item["confidence"] for item in detections]
    finite_scores = [score for score in scores if isfinite(score)]
    count = len(scores)
    raw_count = result["raw_detection_count"]
    # Scene filtresinde kaldırılan kutu NMS duplicate'i değildir.
    nms_count = result.get("nms_detection_count", count)
    duplicates = 1 - nms_count / raw_count if raw_count else 0.0
    weak_fraction = sum(score < threshold * policy.weak_score_multiplier for score in scores) / count if count else 0.0
    valid_geometry = all(
        all(isfinite(value) for value in item["box"].values())
        and item["box"]["xmax"] > item["box"]["xmin"]
        and item["box"]["ymax"] > item["box"]["ymin"]
        for item in detections
    )
    reason = "valid"
    if any(not isfinite(score) or not 0 <= score <= 1 for score in scores) or not valid_geometry:
        reason = "invalid_detection"
    elif raw_count > policy.max_raw_detections or count > policy.max_filtered_detections:
        reason = "detection_explosion"
    elif raw_count >= 10 and duplicates >= policy.max_duplicate_fraction:
        # Çok sayıda raw kutunun tek kutuya çökmesi duplicate baskısını gösterir.
        reason = "duplicate_overload"
    elif not count:
        reason = "empty"
    elif weak_fraction > policy.max_weak_fraction:
        # Eşiğin hemen üstüne yığılmış skorlar kesin yanlış değildir: yedekte tut.
        reason = "weak_confidence_distribution"
    return {
        "threshold": threshold,
        "detections": count,
        "raw_detection_count": raw_count,
        "filtered_detection_count": count,
        "nms_detection_count": nms_count,
        "oversized_boxes_removed": result.get("oversized_boxes_removed", []),
        "oversized_boxes_removed_count": result.get("oversized_boxes_removed_count", 0),
        "scene_box_diagnostics": result.get("scene_box_diagnostics", []),
        "confidence_distribution": {
            # NaN/Inf içeren aday reddedilse bile debug JSON'u geçerli kalmalı.
            "min": min(finite_scores) if finite_scores else None,
            "max": max(finite_scores) if finite_scores else None,
            "mean": sum(finite_scores) / len(finite_scores) if finite_scores else None,
            "weak_fraction": weak_fraction,
        },
        "duplicate_fraction": duplicates,
        "assessment": reason,
    }


def _run_thresholds(
    detector: BaseDetector,
    image,
    query: ProcessedQuery,
    policy: AdaptiveThresholdSettings,
    inference_queries: list[str] | None = None,
) -> DetectorResult:
    """Tek bir query fazının eşiklerini dene; faz içinde otomatik fallback yoktur."""
    attempts = []
    provisional = None
    selected = None
    reason = "no_detections"
    thresholds = policy.thresholds if policy.allow_lowering else policy.thresholds[:1]
    for threshold in thresholds:
        # Fallback listesi boş query planı otomatik erken fallback'i engeller.
        # DINO'nun ayrı box/text ayarları aynen korunur.
        options = {} if policy.text_threshold is None else {"text_threshold": policy.text_threshold}
        if inference_queries is not None:
            options["inference_queries"] = inference_queries
        result = detector.detect_result(image, query, threshold, **options)
        # detect_result zaten mevcut class-aware NMS'i uygular. Kalite/eşik
        # seçimi yalnızca bu ek sanity kontrolünden geçen final kutulara bakar.
        result = apply_scene_box_filter(result, image.size if image is not None else None)
        attempt = evaluate_result(result, threshold, policy)
        attempt["phase"] = "primary" if inference_queries is None else "fallback"
        attempt["queries"] = [query["primary_query"]] if inference_queries is None else list(inference_queries)
        if policy.text_threshold is not None:
            attempt["text_threshold"] = policy.text_threshold
        attempts.append(attempt)
        assessment = attempt["assessment"]
        if assessment == "valid":
            selected = (result, threshold)
            reason = "first_valid_result"
            break
        if assessment == "weak_confidence_distribution" and provisional is None:
            provisional = (result, threshold)
        elif assessment in ("detection_explosion", "duplicate_overload") and provisional is not None:
            selected = provisional
            reason = "previous_controlled_result_preserved"
            break

    if selected is None:
        if provisional is not None:
            selected = provisional
            reason = "best_controlled_result_available"
        else:
            # Aşırı/bozuk kutular kullanıcıya kabul edilmiş sonuç diye verilmez.
            selected = ({**result, "detections": [], "filtered_detection_count": 0}, threshold)
            reason = "no_detections" if all(a["assessment"] == "empty" for a in attempts) else "no_safe_result"
    result, threshold = selected
    return {
        **result,
        "adaptive_threshold_used": threshold,
        "threshold_attempts": attempts,
        "threshold_selection_reason": reason,
    }


def run_detection(
    detector: BaseDetector,
    image,
    query: ProcessedQuery,
    policy: AdaptiveThresholdSettings | None = None,
) -> DetectorResult:
    """Önce primary için adaptive eşikler; ancak hepsi boşsa synonym fazı.

    Primary'nin geçerli veya kontrollü yedek sonucu fallback ile değiştirilmez.
    Aşırı/bozuk primary sonuçlar da synonym genişletmesiyle körlemesine aşılmaz.
    """
    policy = policy if policy is not None else ADAPTIVE_THRESHOLDS[detector.policy_key or detector.model_id]
    from .inventory_service import add_inventory, run_inventory_detection
    if query.get("processed_query_items"):
        return attach_scene_box_diagnostics(run_inventory_detection(detector, image, query, policy, run_detection))
    started = perf_counter()
    primary_plan = {**query, "fallback_queries": []}
    result = _run_thresholds(detector, image, primary_plan, policy)
    primary_attempts = result["threshold_attempts"]
    if config.SYNONYM_FALLBACK_ENABLED and query["fallback_queries"] and all(a["raw_detection_count"] == 0 for a in primary_attempts):
        result = _run_thresholds(detector, image, primary_plan, policy, query["fallback_queries"])
        result["threshold_attempts"] = primary_attempts + result["threshold_attempts"]
    return attach_scene_box_diagnostics(add_inventory({
        **result,
        # Tüm fazlar ve NMS dahil; çeviri/model yükleme hariç toplam süre.
        "inference_time_ms": (perf_counter() - started) * 1000,
        "detections": [{**d, "canonical_query": query["primary_query"]} for d in result["detections"]],
    }, [query["primary_query"]]))
