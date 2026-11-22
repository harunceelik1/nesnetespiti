"""Göreli puan filtresinin ikinci veri doğrulaması: RPC test kümesi (market, çok kopyalı ürünler).

Oran LVIS'te seçildi; burada yalnızca kontrol edilir (RPC test verisiyle oran seçilmez).
Senaryo, filtrenin en riskli olduğu durum: tek sorgu ("product") ve görselde aynı
türden çok sayıda nesne. Her tespit, sınıftan bağımsız olarak herhangi bir ürün
kutusuyla IoU >= 0.5 eşleşirse doğru sayılır.

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.relative_filter_rpc --model owlvit
  .venv\\Scripts\\python.exe -m evaluation.lvis.relative_filter_rpc --report
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import warnings
from pathlib import Path

from evaluation.lvis.evaluate_subset import MODEL_LABELS, OUT_DIR, iou

ROOT = Path(__file__).resolve().parents[2]
RPC = ROOT / "evaluation" / "inventory" / "data"
SAMPLE_SIZE = 60
SEED = 42
QUERY = "product"
RATIOS = (None, 0.3, 0.4, 0.5, 0.6)
POLICY_KEYS = {"owlvit": "owlv2", "yolo-world": "yolo-world"}


def test_images() -> list[dict]:
    images = [i for i in json.loads((RPC / "full_annotations.json").read_text(encoding="utf-8"))["images"]
              if i.get("subset") == "test"]
    images.sort(key=lambda i: i["image_id"])
    return random.Random(SEED).sample(images, SAMPLE_SIZE)


def run_model(model: str) -> None:
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

    detector = DetectorRegistry().get(model)
    key = POLICY_KEYS[model]
    floor = config.SENSITIVITY_THRESHOLDS[key]["loose"]
    policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False)
    plan = process_query(QUERY, TranslationService.__new__(TranslationService), QUERY)
    records = []
    for number, item in enumerate(test_images(), 1):
        with Image.open(RPC / "test" / "images" / item["file_name"]) as source:
            image = source.convert("RGB")
        t = time.perf_counter()
        found = run_detection(detector, image, plan, policy)["detections"]
        records.append({"image_id": item["image_id"],
                        "detections": [{"confidence": round(d["confidence"], 4),
                                        "box": [round(d["box"][k], 1) for k in ("xmin", "ymin", "xmax", "ymax")]}
                                       for d in found]})
        print(f"[{model}] {number}/{SAMPLE_SIZE} {len(found)} kutu {time.perf_counter() - t:.1f}s", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"rpc_tespitler_{model}.json").write_text(json.dumps({"model": model, "floor": floor, "records": records}),
                                                         encoding="utf-8")


def evaluate(records: list[dict], gt: dict[str, list], threshold: float, ratio: float | None) -> dict:
    tp = fp = total = 0
    for record in records:
        boxes = gt[record["image_id"]]
        total += len(boxes)
        kept = [d for d in record["detections"] if d["confidence"] >= threshold]
        if ratio is not None and kept:
            best = max(d["confidence"] for d in kept)
            kept = [d for d in kept if d["confidence"] >= ratio * best]
        used = set()
        for d in sorted(kept, key=lambda d: -d["confidence"]):
            match = max(((iou(d["box"], b), i) for i, b in enumerate(boxes) if i not in used), default=(0, None))
            if match[0] >= 0.5:
                used.add(match[1]); tp += 1
            else:
                fp += 1
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / total if total else 0.0
    return {"tp": tp, "fp": fp, "fn": total - tp, "p": p, "r": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def report() -> None:
    from backend.app import config
    gt = {i["image_id"]: [o["bbox_xyxy"] for o in i["objects"]] for i in test_images()}
    lines = [f"# Göreli filtre · RPC test kümesi ({SAMPLE_SIZE} görsel, sorgu \"{QUERY}\", Dengeli eşik üstüne)", "",
             f"Toplam ürün kutusu: {sum(len(v) for v in gt.values())} (görsel başına ort. "
             f"{sum(len(v) for v in gt.values()) / len(gt):.1f}). Oranlar LVIS'te seçildi, burada yalnızca kontrol edildi.", "",
             "| Model | Oran | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|"]
    for model, key in POLICY_KEYS.items():
        path = OUT_DIR / f"rpc_tespitler_{model}.json"
        if not path.exists():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        threshold = config.ADAPTIVE_THRESHOLDS[key].thresholds[0]
        for ratio in RATIOS:
            s = evaluate(records, gt, threshold, ratio)
            label = "filtresiz" if ratio is None else f"{ratio:.1f}"
            lines.append(f"| {MODEL_LABELS[model]} | {label} | {s['tp']} | {s['fp']} | {s['fn']} | "
                         f"{s['p']:.2f} | {s['r']:.2f} | {s['f1']:.2f} |")
        strict = config.SENSITIVITY_THRESHOLDS[key]["strict"]
        s = evaluate(records, gt, strict, None)
        lines.append(f"| {MODEL_LABELS[model]} | (Sıkı eşik {strict:.2f}) | {s['tp']} | {s['fp']} | {s['fn']} | "
                     f"{s['p']:.2f} | {s['r']:.2f} | {s['f1']:.2f} |")
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "goreli_filtre_rpc.md").write_text(text, encoding="utf-8")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(POLICY_KEYS))
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.model:
        run_model(args.model)
    if args.report:
        report()


if __name__ == "__main__":
    main()
