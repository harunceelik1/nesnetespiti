"""Bir model için sabit eşiği kalibrasyon verisiyle seç.

Düşük bir eşikte (--floor) üretim akışı (çeviri → karşıt sorgu) bir kez çalışır;
bulunan her kutunun puanı kaydedilir:
- Envanter (ornek_envanter, RPC kalibrasyon kümesi) "ürün": GT ile IoU >= 0.5 → TP, değilse FP.
- Olmayan nesne vakaları (evaluation/sanity_cases.py ABSENT): her kutu FP.
Sonra her aday eşik için envanter F1'i ve olmayan nesnelerdeki sahte tespit sayısı yazılır.

Not: Bunlar kalibrasyon görselleridir. Rapordaki son ölçüm RPC test kümesinde
ve ayrı görsellerde yapılmalıdır; aksi halde eşik test verisine uydurulmuş olur.

Kullanım (proje kökünden):
    .\\.venv\\Scripts\\python.exe evaluation/calibrate_threshold.py --model owlvit --floor 0.05
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT / "evaluation" / "inventory"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="owlvit")
    parser.add_argument("--floor", type=float, default=0.05)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    import dataclasses
    from PIL import Image
    from backend.app import config
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService
    from backend.app.utils.nms import calculate_iou
    from quick_product_eval import ANNOTATIONS, SAMPLE_IDS, SAMPLES
    from sanity_cases import CASES

    detector = DetectorRegistry().get(args.model)
    key = detector.policy_key or detector.model_id
    base = config.ADAPTIVE_THRESHOLDS[key]
    policy = dataclasses.replace(base, thresholds=(args.floor,), allow_lowering=False)
    translation = TranslationService()

    # (puan, doğru_mu) envanter; olmayan nesnelerde puanlar
    inventory_scores, gt_total, absent_scores = [], 0, []
    annotations = {im["image_id"]: im for im in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["images"]}
    product = process_query("ürün", translation)
    for number, image_id in enumerate(SAMPLE_IDS, 1):
        gt = [dict(zip(("xmin", "ymin", "xmax", "ymax"), o["bbox_xyxy"])) for o in annotations[image_id]["objects"]]
        gt_total += len(gt)
        with Image.open(SAMPLES / f"{number:02d}_envanter.jpg") as source:
            image = source.convert("RGB")
        found = run_detection(detector, image, product, policy)["detections"]
        # Confidence sırasıyla açgözlü bire bir eşleşme (IoU >= 0.5); her GT bir kez.
        used = set()
        for detection in sorted(found, key=lambda d: -d["confidence"]):
            best, best_index = 0.5, None
            for index, box in enumerate(gt):
                if index not in used:
                    iou = calculate_iou(detection["box"], box)
                    if iou >= best:
                        best, best_index = iou, index
            if best_index is not None:
                used.add(best_index)
            inventory_scores.append((detection["confidence"], best_index is not None))
        print(f"envanter {number:02d}: {len(found)} kutu", flush=True)

    images = {}
    for kind, path, query in CASES:
        if kind != "ABSENT" or not path.is_file():
            continue
        image = images.setdefault(path, Image.open(path).convert("RGB"))
        found = run_detection(detector, image, process_query(query, translation), policy)["detections"]
        absent_scores += [d["confidence"] for d in found]
        print(f"yok {path.stem} {query}: {[round(d['confidence'], 3) for d in found]}", flush=True)

    print(f"\nmodel={args.model} ({key}), GT ürün={gt_total}")
    print("eşik   TP  FP  precision recall  F1    | olmayan nesnede sahte kutu")
    candidates = sorted({round(args.floor + i * 0.01, 2) for i in range(0, 60)})
    for threshold in candidates:
        tp = sum(ok for score, ok in inventory_scores if score >= threshold)
        fp = sum(not ok for score, ok in inventory_scores if score >= threshold)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / gt_total if gt_total else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        fake = sum(score >= threshold for score in absent_scores)
        print(f"{threshold:.2f}  {tp:3d} {fp:3d}   {precision:.2f}     {recall:.2f}   {f1:.2f}  | {fake}")


if __name__ == "__main__":
    main()
