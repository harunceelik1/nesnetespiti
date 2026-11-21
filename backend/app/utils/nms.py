from math import hypot, isfinite


def calculate_iou(box_a: dict, box_b: dict) -> float:
    """İki kutunun kesişim alanının birleşim alanına oranını hesaplar."""
    intersection_width = max(
        0.0, min(box_a["xmax"], box_b["xmax"]) - max(box_a["xmin"], box_b["xmin"])
    )
    intersection_height = max(
        0.0, min(box_a["ymax"], box_b["ymax"]) - max(box_a["ymin"], box_b["ymin"])
    )
    intersection = intersection_width * intersection_height

    area_a = max(0.0, box_a["xmax"] - box_a["xmin"]) * max(
        0.0, box_a["ymax"] - box_a["ymin"]
    )
    area_b = max(0.0, box_b["xmax"] - box_b["xmin"]) * max(
        0.0, box_b["ymax"] - box_b["ymin"]
    )
    # IoU 0 ise örtüşme yoktur, 1 ise kutular tamamen örtüşür.
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def class_aware_nms(detections: list[dict], iou_threshold: float = 0.60) -> list[dict]:
    """Aynı sınıftaki yüksek oranda örtüşen kutuları confidence sırasıyla eler."""
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("IoU threshold 0 ile 1 arasında olmalıdır.")

    # NMS önce en yüksek confidence değerini korur; girdi listesini değiştirmez.
    sorted_detections = sorted(
        detections, key=lambda detection: detection["confidence"], reverse=True
    )
    kept = []
    for detection in sorted_detections:
        # Yalnızca aynı label/query için karşılaştır: farklı sınıflar birbirini elemez.
        overlaps = any(
            detection["label"] == previous["label"]
            and calculate_iou(detection["box"], previous["box"]) > iou_threshold
            for previous in kept
        )
        if not overlaps:
            kept.append(detection)

    return kept


def calculate_containment(box_a: dict, box_b: dict) -> float:
    """Kesişim alanını küçük kutunun alanına bölerek kapsanma oranını hesaplar."""
    width = max(
        0.0, min(box_a["xmax"], box_b["xmax"]) - max(box_a["xmin"], box_b["xmin"])
    )
    height = max(
        0.0, min(box_a["ymax"], box_b["ymax"]) - max(box_a["ymin"], box_b["ymin"])
    )
    intersection = width * height
    area_a = max(0.0, box_a["xmax"] - box_a["xmin"]) * max(
        0.0, box_a["ymax"] - box_a["ymin"]
    )
    area_b = max(0.0, box_b["xmax"] - box_b["xmin"]) * max(
        0.0, box_b["ymax"] - box_b["ymin"]
    )
    # IoU birleşim alanını kullanır; containment küçük kutunun kapsanmasını ölçer.
    # İç içe kutularda IoU düşük olsa da containment 1 olabilir.
    smaller_area = min(area_a, area_b)
    return intersection / smaller_area if smaller_area > 0 else 0.0


def calculate_normalized_center_distance(box_a: dict, box_b: dict) -> float:
    """Merkez uzaklığını alanı büyük kutunun diagonal uzunluğuna böler."""
    center_a = ((box_a["xmin"] + box_a["xmax"]) / 2, (box_a["ymin"] + box_a["ymax"]) / 2)
    center_b = ((box_b["xmin"] + box_b["xmax"]) / 2, (box_b["ymin"] + box_b["ymax"]) / 2)
    width_a = max(0.0, box_a["xmax"] - box_a["xmin"])
    height_a = max(0.0, box_a["ymax"] - box_a["ymin"])
    width_b = max(0.0, box_b["xmax"] - box_b["xmin"])
    height_b = max(0.0, box_b["ymax"] - box_b["ymin"])

    area_a, area_b = width_a * height_a, width_b * height_b
    if area_a > area_b:
        diagonal = hypot(width_a, height_a)
    elif area_b > area_a:
        diagonal = hypot(width_b, height_b)
    else:
        # Eşit alanlarda karşılaştırmanın sırasından bağımsız bir ölçek kullan.
        diagonal = max(hypot(width_a, height_a), hypot(width_b, height_b))

    distance = hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
    # Normalizasyon, aynı kutular yeniden ölçeklense de sonucu değiştirmez.
    return distance / diagonal if diagonal > 0 else float("inf")


def suppress_contained_duplicates(
    detections: list[dict],
    containment_threshold: float = 0.80,
    normalized_center_distance_threshold: float = 0.15,
) -> list[dict]:
    """NMS sonrasında aynı label'a sahip, merkezleri yakın iç içe kutuları eler."""
    if not 0.0 <= containment_threshold <= 1.0:
        raise ValueError("Containment threshold 0 ile 1 arasında olmalıdır.")
    if not isfinite(normalized_center_distance_threshold) or normalized_center_distance_threshold < 0:
        raise ValueError("Merkez uzaklığı threshold değeri sonlu ve negatif olmayan bir sayı olmalıdır.")

    # Kutunun büyüklüğünden bağımsız olarak yüksek confidence değerini koru.
    sorted_detections = sorted(
        detections, key=lambda detection: detection["confidence"], reverse=True
    )
    kept = []
    for detection in sorted_detections:
        # Yüksek containment, üst üste duran farklı nesnelerde de oluşabilir.
        # Merkezler uzaksa iki kutuyu koru; yalnızca yakın merkezli kutuları ele.
        duplicate = any(
            detection["label"] == previous["label"]
            and calculate_containment(detection["box"], previous["box"])
            >= containment_threshold
            and calculate_normalized_center_distance(detection["box"], previous["box"])
            <= normalized_center_distance_threshold
            for previous in kept
        )
        if not duplicate:
            kept.append(detection)

    return kept
