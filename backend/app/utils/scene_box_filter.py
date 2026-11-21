"""Production NMS sonrası conservative scene-box kontrolü; confidence/NMS değiştirmez."""

from math import isfinite

from ..config import SCENE_BOX_FILTER, SceneBoxFilterSettings


def scene_box_rule(area_ratio: float, touched_edges: int,
                   settings: SceneBoxFilterSettings = SCENE_BOX_FILTER, *,
                   width_coverage: float | None = None, height_coverage: float | None = None) -> str | None:
    """A/B korunur; C ayrıca bir eksenin neredeyse tam kaplanmasını gerektirir."""
    if area_ratio >= settings.min_area_ratio and touched_edges >= settings.min_near_borders:
        return "rule_a"
    if area_ratio >= settings.full_scene_min_area_ratio and touched_edges == settings.full_scene_near_borders:
        return "rule_b"
    if (width_coverage is not None and height_coverage is not None
            and area_ratio >= settings.axis_scene_min_area_ratio
            and touched_edges >= settings.axis_scene_min_near_borders
            and max(width_coverage, height_coverage) >= settings.axis_scene_long_coverage
            and min(width_coverage, height_coverage) >= settings.axis_scene_short_coverage):
        return "rule_c"
    return None


def filter_scene_boxes(
    detections: list[dict], image_size: tuple[int, int],
    settings: SceneBoxFilterSettings = SCENE_BOX_FILTER,
    *, diagnostics: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    width, height = image_size
    if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0:
        raise ValueError("Scene-box filtresi için geçerli görüntü boyutu gerekir.")
    kept, removed = [], []
    for detection in detections:
        box = detection["box"]
        xmin, ymin, xmax, ymax = (box[key] for key in ("xmin", "ymin", "xmax", "ymax"))
        if not all(isfinite(value) for value in (xmin, ymin, xmax, ymax)) or xmax <= xmin or ymax <= ymin:
            # Bozuk geometriyi bu heuristikle gizleme; mevcut adaptive kontrolüne bırak.
            kept.append(detection)
            continue
        if not isfinite(detection["confidence"]) or not 0 <= detection["confidence"] <= 1:
            # Geçersiz skoru kaldırma metadata'sına taşıyarak JSON'u bozma veya
            # mevcut invalid_detection değerlendirmesinden gizleme.
            kept.append(detection)
            continue
        area_ratio = (xmax - xmin) * (ymax - ymin) / (width * height)
        width_coverage = (xmax - xmin) / width
        height_coverage = (ymax - ymin) / height
        distances = {"left": abs(xmin) / width, "right": abs(width - xmax) / width,
                     "top": abs(ymin) / height, "bottom": abs(height - ymax) / height}
        near_borders = [name for name, distance in distances.items()
                        if distance <= settings.border_tolerance_ratio]
        # B kuralında daha düşük alan ancak dört kenar da yakınsa kabul edilir.
        # Koordinatları clip/resize etmeyiz; normal büyük nesneler aynen korunur.
        rule = scene_box_rule(area_ratio, len(near_borders), settings,
                              width_coverage=width_coverage, height_coverage=height_coverage)
        entry = {"detection": detection, "area_ratio": area_ratio,
                 "width_coverage": width_coverage, "height_coverage": height_coverage,
                 "box_area": (xmax - xmin) * (ymax - ymin), "image_area": width * height,
                 "image_size": {"width": width, "height": height},
                 "edge_distance_ratios": distances, "near_borders": near_borders,
                 "touched_edges": len(near_borders), "matched_rule": rule, "removed": rule is not None,
                 "reason": "oversized_scene_box" if rule else "scene_box_criteria_not_met"}
        if diagnostics is not None:
            diagnostics.append(entry)
        if rule:
            removed.append(entry)
        else:
            kept.append(detection)
    return kept, removed


def apply_scene_box_filter(result: dict, image_size: tuple[int, int] | None) -> dict:
    # Eski model indirmeyen orchestration testleri image=None kullanabilir.
    # HTTP production akışı her zaman decode edilmiş PIL görüntü boyutu verir.
    detections = result["detections"]
    diagnostics = []
    kept, removed = filter_scene_boxes(detections, image_size, diagnostics=diagnostics) if image_size is not None else (detections, [])
    return {**result, "detections": kept, "nms_detection_count": len(detections),
            "filtered_detection_count": len(kept), "oversized_boxes_removed": removed,
            "oversized_boxes_removed_count": len(removed), "scene_box_diagnostics": diagnostics}


def attach_scene_box_diagnostics(result: dict) -> dict:
    """Tüm denemelerin kaldırmalarını kaydet; aynı kutu farklı eşikte tekrar görünebilir."""
    removed = [{**entry, "threshold": attempt["threshold"], "phase": attempt["phase"],
                "canonical_query": attempt.get("canonical_query", result["primary_query"])}
               for attempt in result["threshold_attempts"] for entry in attempt["oversized_boxes_removed"]]
    diagnostics = [{**entry, "threshold": attempt["threshold"], "phase": attempt["phase"],
                    "canonical_query": attempt.get("canonical_query", result["primary_query"])}
                   for attempt in result["threshold_attempts"] for entry in attempt.get("scene_box_diagnostics", [])]
    return {**result, "oversized_boxes_removed": removed, "oversized_boxes_removed_count": len(removed),
            "scene_box_diagnostics": diagnostics,
            "scene_box_filter": {"min_area_ratio": SCENE_BOX_FILTER.min_area_ratio,
                                 "border_tolerance_ratio": SCENE_BOX_FILTER.border_tolerance_ratio,
                                 "min_near_borders": SCENE_BOX_FILTER.min_near_borders,
                                 "full_scene_min_area_ratio": SCENE_BOX_FILTER.full_scene_min_area_ratio,
                                 "full_scene_near_borders": SCENE_BOX_FILTER.full_scene_near_borders,
                                 "axis_scene_min_area_ratio": SCENE_BOX_FILTER.axis_scene_min_area_ratio,
                                 "axis_scene_min_near_borders": SCENE_BOX_FILTER.axis_scene_min_near_borders,
                                 "axis_scene_long_coverage": SCENE_BOX_FILTER.axis_scene_long_coverage,
                                 "axis_scene_short_coverage": SCENE_BOX_FILTER.axis_scene_short_coverage},
            "oversized_box_diagnostics_scope": "all_threshold_attempts"}
