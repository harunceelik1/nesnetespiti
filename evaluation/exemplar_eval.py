"""Örnekle arama (OWLv2 image-guided) için eşik ölçümü — RPC kalibrasyon kümesi.

Her görselde birden fazla kopyası olan bir ürün (aynı SKU) seçilir; ilk kopyanın GT
kutusu kullanıcının çizdiği örnek kutu sayılır. Beklenen: aynı SKU'nun tüm kopyaları.
- TP: aynı SKU'lu diğer bir kopya ile IoU >= 0.5 eşleşen kutu (örneğin kendisi sayılmaz).
- FP: başka bir ürüne ya da boşluğa düşen kutu (benzer ama farklı ürün dahil).
- "Sayı doğru": bulunan kutu sayısı == aynı SKU kopya sayısı ve FP yok.

Kullanım (proje kökünden):
    .\\.venv\\Scripts\\python.exe evaluation/exemplar_eval.py --subset calibration --per-image 1
    .\\.venv\\Scripts\\python.exe evaluation/exemplar_eval.py --subset test --per-image 1 --limit 60
"""

import argparse
import collections
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "evaluation" / "inventory" / "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", default="calibration", choices=("calibration", "test"))
    parser.add_argument("--per-image", type=int, default=1, help="görsel başına en fazla kaç ürün denensin")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dump", type=Path, help="ham puanları JSON olarak kaydet")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    from PIL import Image
    from backend.app.models.owlv2_service import Owlv2Service
    from backend.app.utils.nms import calculate_iou

    detector = Owlv2Service()
    records = json.loads((DATA / args.subset / "annotations.json").read_text(encoding="utf-8"))
    records = records["images"] if isinstance(records, dict) else records
    if args.limit:
        records = records[:args.limit]

    trials = []  # her deneme: aday puan/kutu listesi + GT
    for record in records:
        by_sku = collections.defaultdict(list)
        for obj in record["objects"]:
            by_sku[obj["original_category_id"]].append(dict(zip(("xmin", "ymin", "xmax", "ymax"), obj["bbox_xyxy"])))
        repeated = sorted((boxes for boxes in by_sku.values() if len(boxes) > 1), key=len, reverse=True)
        if not repeated:
            continue
        with Image.open(DATA / args.subset / "images" / record["file_name"]) as source:
            image = source.convert("RGB")
        others_all = [dict(zip(("xmin", "ymin", "xmax", "ymax"), o["bbox_xyxy"])) for o in record["objects"]]
        for same in repeated[:args.per_image]:
            candidates, chosen = detector.example_candidates(image, same[0])
            # Eşikten bağımsız ön eleme: çok düşük puanlar hiçbir eşikte seçilmez.
            candidates = [c for c in candidates if c["objectness"] >= 0.01 and c["similarity"] >= 0.5]
            others = [box for box in others_all if box not in same]
            trials.append({"image": record["file_name"], "same": same, "others": others,
                           "candidates": candidates, "chosen_iou": calculate_iou(chosen, same[0])})
            print(f"{record['file_name']}: kopya={len(same)} aday={len(candidates)} "
                  f"seçilen kutu IoU={trials[-1]['chosen_iou']:.2f}", flush=True)

    if args.dump:
        args.dump.write_text(json.dumps(trials), encoding="utf-8")
    report(trials)


def evaluate(trials, threshold):
    """Üretimdeki süzgeç (benzerlik + objectness + NMS/kapsama) ile tek eşik.

    Örnek kutunun kendisi sayılmaz: "diğer kopyalar" metriği asıl başarıyı ölçer.
    """
    import dataclasses
    from backend.app import config
    from backend.app.services.exemplar_search import _suppress
    from backend.app.utils.nms import calculate_iou
    settings = dataclasses.replace(config.EXEMPLAR_SEARCH, similarity_threshold=threshold)
    tp = fp = other = gt = exact = 0
    for trial in trials:
        passed = [c for c in trial["candidates"]
                  if c["similarity"] >= threshold and c["objectness"] >= settings.min_objectness]
        kept = _suppress(passed, settings)
        used = set()
        for det in kept:
            match = next((i for i, box in enumerate(trial["same"])
                          if i not in used and calculate_iou(det["box"], box) >= 0.5), None)
            if match is not None:
                used.add(match)
            else:
                fp += 1
                other += any(calculate_iou(det["box"], box) >= 0.5 for box in trial["others"])
        tp += len(used - {0})
        gt += len(trial["same"]) - 1
        exact += (len(used) == len(trial["same"]) and len(kept) == len(used))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / gt if gt else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return tp, fp, other, precision, recall, f1, exact


def report(trials):
    from backend.app import config
    print(f"\ndeneme={len(trials)}  diğer kopya (örnek hariç)={sum(len(t['same']) - 1 for t in trials)}"
          f"  üretim eşiği={config.EXEMPLAR_SEARCH.similarity_threshold}")
    print("eşik   TP   FP (farklı ürün)  precision recall  F1   | sayı tam doğru")
    for step in range(80, 98, 2):
        threshold = step / 100
        tp, fp, other, p, r, f1, exact = evaluate(trials, threshold)
        print(f"{threshold:.2f}  {tp:4d} {fp:4d} ({other:3d})        {p:.2f}     {r:.2f}   {f1:.2f} | {exact}/{len(trials)}")


if __name__ == "__main__":
    main()
