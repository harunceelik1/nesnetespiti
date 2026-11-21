"""Detection/counting metrikleri: saf Python, model veya dataset bağımlılığı yok."""

from math import isfinite


def xyxy(box) -> tuple[float, float, float, float]:
    if isinstance(box, dict):
        box = [box[key] for key in ("xmin", "ymin", "xmax", "ymax")]
    if len(box) != 4 or any(type(value) not in (int, float) or not isfinite(value) for value in box):
        raise ValueError("XYXY kutusu dört sonlu sayı içermelidir.")
    xmin, ymin, xmax, ymax = map(float, box)
    if xmax < xmin or ymax < ymin:
        raise ValueError("XYXY kutusunun min/max sırası geçersiz.")
    return xmin, ymin, xmax, ymax


def iou(box_a, box_b) -> float:
    ax1, ay1, ax2, ay2 = xyxy(box_a)
    bx1, by1, bx2, by2 = xyxy(box_b)
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
    return intersection / union if union > 0 else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall,
            "F1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def evaluate_boxes(predictions: list[dict], ground_truth: list, iou_threshold: float = 0.5) -> dict:
    """Tek kategori için confidence-ordered greedy one-to-one matching.

    Eşit confidence'ta input indeksi, eşit IoU'da GT indeksi tie-break olur.
    Kullanılmış GT tekrar TP olamaz; prediction da en fazla bir GT alır.
    """
    if not isfinite(iou_threshold) or not 0 < iou_threshold <= 1:
        raise ValueError("Matching IoU threshold (0, 1] aralığında olmalıdır.")
    gt_boxes = [xyxy(box) for box in ground_truth]
    pred_boxes = [xyxy(item["box"]) for item in predictions]
    for item in predictions:
        score = item["confidence"]
        if type(score) not in (int, float) or not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Prediction confidence [0, 1] aralığında sonlu sayı olmalıdır.")
    order = sorted(range(len(predictions)), key=lambda index: (-predictions[index]["confidence"], index))
    used = set()
    matches = []
    for pred_index in order:
        options = [(iou(pred_boxes[pred_index], box), gt_index)
                   for gt_index, box in enumerate(gt_boxes) if gt_index not in used]
        if not options:
            continue
        overlap, gt_index = max(options, key=lambda option: (option[0], -option[1]))
        if overlap >= iou_threshold:
            used.add(gt_index)
            matches.append({"prediction_index": pred_index, "ground_truth_index": gt_index, "iou": overlap})
    tp = len(matches)
    fp, fn = len(predictions) - tp, len(ground_truth) - tp
    return {
        "ground_truth_count": len(ground_truth), "predicted_count": len(predictions),
        "TP": tp, "FP": fp, "FN": fn, **precision_recall_f1(tp, fp, fn),
        "average_matched_iou": sum(item["iou"] for item in matches) / tp if tp else None,
        "count_absolute_error": abs(len(predictions) - len(ground_truth)), "matches": matches,
    }


def summarize(records: list[dict], categories: tuple[str, ...], image_runs: list[dict]) -> dict:
    """Micro tüm kutulardan, macro sınıf başına toplamlardan hesaplanır.

    MAE image/category kayıtları üzerindedir. Inference süresi image_runs'dan
    alınır; aynı 17-sorgulu çağrı süresi 17 kez toplanmaz.
    """
    per_category = []
    for category in categories:
        rows = [row for row in records if row["category"] == category]
        totals = {key: sum(row[key] for row in rows) for key in ("TP", "FP", "FN")}
        per_category.append({"category": category, **totals, **precision_recall_f1(totals["TP"], totals["FP"], totals["FN"])})
    totals = {key: sum(row[key] for row in records) for key in ("TP", "FP", "FN")}
    micro = precision_recall_f1(totals["TP"], totals["FP"], totals["FN"])
    all_ious = [match["iou"] for row in records for match in row["matches"]]
    return {
        **totals, "micro_precision": micro["precision"], "micro_recall": micro["recall"], "micro_F1": micro["F1"],
        "macro_precision": sum(row["precision"] for row in per_category) / len(categories) if categories else 0.0,
        "macro_recall": sum(row["recall"] for row in per_category) / len(categories) if categories else 0.0,
        "macro_F1": sum(row["F1"] for row in per_category) / len(categories) if categories else 0.0,
        "mean_matched_iou": sum(all_ious) / len(all_ious) if all_ious else None,
        "mean_absolute_counting_error": sum(row["count_absolute_error"] for row in records) / len(records) if records else 0.0,
        "average_inference_time_ms": sum(run["inference_time_ms"] for run in image_runs) / len(image_runs) if image_runs else None,
        "images_evaluated": len(image_runs), "image_category_records": len(records), "per_category": per_category,
    }
