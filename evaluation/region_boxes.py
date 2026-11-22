"""Bölge kutusu ölçümü: model nesnenin kendisi yerine birkaç nesneyi saran kutu mu çiziyor?

RPC kalibrasyon kümesinde (her nesnenin GT kutusu ve kategorisi var) üretim akışı
(çeviri yok: İngilizce ifade doğrudan verilir → karşıt sorgu → kalibre eşik) çalışır.
Her görselde "product" ve görselde bulunan her kategori (ör. "instant noodles") sorulur.

Bulunan her kutu şu sırayla sınıflanır:
- doğru: sorulan kategoriden eşleşmemiş bir GT ile IoU >= 0.5
- bölge: en az 2 GT nesnesini (her birinin alanının >= %80'i) içine alıyor
- yanlış ürün: başka kategoriden bir GT ile IoU >= 0.5 (yalnızca kategori sorgularında)
- diğer: parça, kayık ya da boşluktaki kutu
Bölge kutusu için ayrıca: içindeki nesneler aynı kategoriden mi (grup) karışık mı,
ve puanı içindeki en iyi doğru kutudan yüksek mi ("bölge önde").

Kullanım (proje kökünden):
    .\\.venv\\Scripts\\python.exe evaluation/region_boxes.py --model owlvit --limit 20
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
DATA = ROOT / "evaluation" / "inventory" / "data" / "calibration"
KINDS = ("doğru", "bölge", "yanlış ürün", "diğer")


def inside_ratio(gt, box):
    """GT kutusunun alanının ne kadarı box içinde."""
    w = max(0.0, min(gt["xmax"], box["xmax"]) - max(gt["xmin"], box["xmin"]))
    h = max(0.0, min(gt["ymax"], box["ymax"]) - max(gt["ymin"], box["ymin"]))
    area = (gt["xmax"] - gt["xmin"]) * (gt["ymax"] - gt["ymin"])
    return w * h / area if area > 0 else 0.0


def classify(detections, objects, category):
    from backend.app.utils.nms import calculate_iou
    used, rows = set(), []
    for det in sorted(detections, key=lambda d: -d["confidence"]):
        box = det["box"]
        match = next((i for i, o in enumerate(objects) if i not in used
                      and (category is None or o["category"] == category)
                      and calculate_iou(box, o["box"]) >= 0.5), None)
        covered = [o for o in objects if inside_ratio(o["box"], box) >= 0.8]
        if match is not None:
            used.add(match)
            kind = "doğru"
        elif len(covered) >= 2:
            kind = "bölge"
        elif category is not None and any(calculate_iou(box, o["box"]) >= 0.5 for o in objects):
            kind = "yanlış ürün"
        else:
            kind = "diğer"
        rows.append({"kind": kind, "confidence": det["confidence"], "box": box, "covered": covered})
    # Bölge kutusu, içindeki doğru kutulardan yüksek puanlı mı?
    for row in rows:
        if row["kind"] == "bölge":
            inner = [r["confidence"] for r in rows if r["kind"] == "doğru" and inside_ratio(r["box"], row["box"]) >= 0.8]
            row["ahead"] = not inner or row["confidence"] > max(inner)
            row["group"] = category is not None and all(o["category"] == category for o in row["covered"])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="owlvit")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--save", type=int, default=6, help="kaç bölge kutusu örneği kaydedilsin")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    from PIL import Image
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.utils.visualization import annotate_image

    detector = DetectorRegistry().get(args.model)
    records = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))[:args.limit]
    out_dir = ROOT / "outputs" / "bolge_kutusu" / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = collections.defaultdict(collections.Counter)  # sorgu türü → sayaç
    saved = 0
    for record in records:
        objects = [{"category": o["evaluation_category"],
                    "box": dict(zip(("xmin", "ymin", "xmax", "ymax"), o["bbox_xyxy"]))} for o in record["objects"]]
        with Image.open(DATA / "images" / record["file_name"]) as source:
            image = source.convert("RGB")
        queries = [("ürün", "product", None)] + [(c, c, c) for c in sorted({o["category"] for o in objects})]
        for label, english, category in queries:
            plan = process_query(label, None, english_query=english)
            detections = run_detection(detector, image, plan)["detections"]
            rows = classify(detections, objects, category)
            kind = "ürün" if category is None else "kategori"
            counter = stats[kind]
            counter["sorgu"] += 1
            counter["GT"] += sum(category is None or o["category"] == category for o in objects)
            counter.update(r["kind"] for r in rows)
            regions = [r for r in rows if r["kind"] == "bölge"]
            counter["bölgeli sorgu"] += bool(regions)
            counter["bölge önde"] += sum(r["ahead"] for r in regions)
            counter["bölge aynı kategori"] += sum(r["group"] for r in regions)
            if regions:
                print(f"{record['file_name']} {english!r}: bölge {len(regions)} "
                      f"(puan {[round(r['confidence'], 2) for r in regions]}, "
                      f"kapsadığı {[len(r['covered']) for r in regions]}), doğru {sum(r['kind'] == 'doğru' for r in rows)}",
                      flush=True)
                if saved < args.save:
                    marked = [{"label": ("BÖLGE " if r["kind"] == "bölge" else "") + english,
                               "confidence": r["confidence"], "box": r["box"]} for r in rows]
                    with annotate_image(image, marked) as annotated:
                        annotated.save(out_dir / f"{Path(record['file_name']).stem}_{english.replace(' ', '_')}.jpg")
                    saved += 1

    print(f"\nmodel={args.model}  görsel={len(records)}")
    for kind, c in stats.items():
        total = sum(c[k] for k in KINDS)
        print(f"\n[{kind}] sorgu={c['sorgu']}  GT={c['GT']}  bulunan kutu={total}")
        for k in KINDS:
            print(f"  {k:12s} {c[k]:4d}  ({c[k] / total:.0%})" if total else f"  {k:12s} 0")
        print(f"  bölge kutusu çıkan sorgu: {c['bölgeli sorgu']}/{c['sorgu']}")
        if c["bölge"]:
            print(f"  bölge, içindeki doğru kutudan yüksek puanlı: {c['bölge önde']}/{c['bölge']}")
            print(f"  bölge yalnızca sorulan kategoriyi sarıyor (grup): {c['bölge aynı kategori']}/{c['bölge']}")


if __name__ == "__main__":
    main()
