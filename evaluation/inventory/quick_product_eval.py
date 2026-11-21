"""Örnek envanter görsellerinde üretim akışıyla hızlı ölçüm (sınıftan bağımsız ürün sayımı).

Her görselde backend'in gerçek akışı çalışır (çeviri → karşıt sorgu → adaptive eşik):
- "ürün": tahminler GT kutularıyla IoU >= 0.5 açgözlü eşleşir → precision/recall/sayım hatası.
- "köpek": görselde yok; bulunan her kutu sahte tespittir.
- "şişe": yalnızca bulunan sayı (RPC kategorileri şekil bilgisi taşımaz).

Kullanım (proje kökünden):
    .\\.venv\\Scripts\\python.exe evaluation/inventory/quick_product_eval.py --models owlvit,grounding-dino
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "ornek_envanter"
ANNOTATIONS = ROOT / "evaluation" / "inventory" / "data" / "full_annotations.json"
# ornek_envanter/NN_envanter.jpg sırası (README ile aynı).
SAMPLE_IDS = [
    "rpc-validation-00000-000433", "rpc-validation-00001-000395", "rpc-validation-00000-000083",
    "rpc-validation-00001-000216", "rpc-validation-00000-000294", "rpc-validation-00000-000087",
    "rpc-validation-00003-000266", "rpc-validation-00000-000321", "rpc-validation-00003-000154",
    "rpc-validation-00003-000439", "rpc-validation-00002-000388", "rpc-validation-00002-000012",
]


def greedy_tp(predictions, ground_truth, iou_threshold=0.5):
    from backend.app.utils.nms import calculate_iou
    used, tp = set(), 0
    for pred in sorted(predictions, key=lambda d: -d["confidence"]):
        best, best_index = iou_threshold, None
        for index, gt in enumerate(ground_truth):
            if index not in used:
                iou = calculate_iou(pred["box"], gt)
                if iou >= best:
                    best, best_index = iou, index
        if best_index is not None:
            used.add(best_index)
            tp += 1
    return tp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="owlvit,grounding-dino")
    parser.add_argument("--limit", type=int, default=len(SAMPLE_IDS))
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT))
    from PIL import Image
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService

    translation = TranslationService()
    registry = DetectorRegistry()
    detectors = {name: registry.get(name) for name in args.models.split(",")}
    annotations = {im["image_id"]: im for im in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["images"]}
    plans = {query: process_query(query, translation) for query in ("ürün", "köpek", "şişe")}
    totals = {name: {"tp": 0, "fp": 0, "fn": 0, "abs_err": 0, "dog": 0} for name in detectors}

    for number, image_id in enumerate(SAMPLE_IDS[: args.limit], 1):
        gt = [dict(zip(("xmin", "ymin", "xmax", "ymax"), o["bbox_xyxy"])) for o in annotations[image_id]["objects"]]
        with Image.open(SAMPLES / f"{number:02d}_envanter.jpg") as source:
            image = source.convert("RGB")
        parts = []
        for name, detector in detectors.items():
            result = run_detection(detector, image, plans["ürün"])
            predictions = result["detections"]
            tp = greedy_tp(predictions, gt)
            dogs = len(run_detection(detector, image, plans["köpek"])["detections"])
            bottles = len(run_detection(detector, image, plans["şişe"])["detections"])
            total = totals[name]
            total["tp"] += tp
            total["fp"] += len(predictions) - tp
            total["fn"] += len(gt) - tp
            total["abs_err"] += abs(len(predictions) - len(gt))
            total["dog"] += dogs
            parts.append(f"{name}: ürün {len(predictions)}/{len(gt)} TP={tp} "
                         f"eşik={result.get('adaptive_threshold_used')} ({result['threshold_selection_reason']}) "
                         f"| köpek={dogs} şişe={bottles}")
        print(f"{number:02d} " + " || ".join(parts), flush=True)

    count = min(args.limit, len(SAMPLE_IDS))
    for name, t in totals.items():
        precision = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
        recall = t["tp"] / (t["tp"] + t["fn"]) if t["tp"] + t["fn"] else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        print(f"TOPLAM {name}: precision={precision:.2f} recall={recall:.2f} F1={f1:.2f} "
              f"ort_sayım_hatası={t['abs_err'] / count:.2f} sahte_köpek={t['dog']}", flush=True)


if __name__ == "__main__":
    main()
