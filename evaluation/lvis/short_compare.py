r"""Kısa karşılaştırma: aynı 20 nadir-nesne görselinde modeller (LLMDet tam ölçülmeden karar için).

Eşik sorunu: adayların kalibre eşiği yok. Adil olsun diye her model kendi **en iyi eşiğinde**
(bu 20 görselde F1'i en yüksek yapan eşik) değerlendirilir; hepsine aynı iyimser muamele.
Nadir 'var' sorusu: görselin LVIS r-sınıfı nesnesi; 'yok' sorusu: doğrulanmış olmayan nesne.

Kullanım: .venv\Scripts\python.exe -m evaluation.lvis.short_compare
"""

from __future__ import annotations

import json

from evaluation.lvis.evaluate_subset import MODEL_LABELS, OUT_DIR, detections_path, iou, subset_path
from evaluation.lvis.frequency_report import FREQUENCY

MODELS = ("owlvit", "owlv2-large", "grounding-dino", "llmdet", "yolo-world")
REFERENCE = "llmdet"


def evaluate(records: list[dict], subset: dict, threshold: float) -> dict:
    t = dict(tp=0, fp=0, gt=0, var=0, bulunan=0, nadir_var=0, nadir_bulunan=0, yok=0, uydurma=0)
    for record in records:
        item = subset[record["image_id"]]
        kept = [d for d in record["detections"] if d["confidence"] >= threshold]
        for category in record["positives"]:
            gt = [[x, y, x + w, y + h] for x, y, w, h in item["positives"][category]]
            used = set()
            for d in sorted((d for d in kept if d["category"] == category), key=lambda d: -d["confidence"]):
                best, best_i = 0.5, None
                for i, g in enumerate(gt):
                    if i not in used and iou(d["box"], g) >= best:
                        best, best_i = iou(d["box"], g), i
                if best_i is None:
                    t["fp"] += 1
                else:
                    used.add(best_i); t["tp"] += 1
            t["gt"] += len(gt); t["var"] += 1; t["bulunan"] += bool(used)
            if FREQUENCY[category] == "r":
                t["nadir_var"] += 1; t["nadir_bulunan"] += bool(used)
        for category in record["negatives"]:
            boxes = [d for d in kept if d["category"] == category]
            t["yok"] += 1; t["uydurma"] += bool(boxes); t["fp"] += len(boxes)
    p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
    r = t["tp"] / t["gt"] if t["gt"] else 0.0
    return {**t, "p": p, "r": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "esik": threshold}


def main() -> None:
    subset = {i["image_id"]: i for i in json.loads(subset_path("nadir").read_text(encoding="utf-8"))}
    ids = [r["image_id"] for r in json.loads(detections_path("nadir", REFERENCE).read_text(encoding="utf-8"))["records"]]
    lines = [f"# Kısa karşılaştırma: aynı {len(ids)} nadir-nesne görseli (LVIS r)", "",
             "Her model kendi en iyi eşiğinde (bu görsellerde F1'i en yüksek eşik).", "",
             "| Model | En iyi eşik | Nadir nesneyi bulduğu | Tüm 'var' soruları | Precision | Recall | F1 | Olmayan nesneye kutu |",
             "|---|---|---|---|---|---|---|---|"]
    for model in MODELS:
        path = detections_path("nadir", model)
        if not path.exists():
            continue
        records = [r for r in json.loads(path.read_text(encoding="utf-8"))["records"] if r["image_id"] in ids]
        if len(records) < len(ids):
            lines.append(f"| {MODEL_LABELS[model]} | — | eksik ({len(records)}/{len(ids)} görsel) | | | | | |")
            continue
        floor = min((d["confidence"] for r in records for d in r["detections"]), default=0.0)
        grid = [round(floor + 0.01 * k, 2) for k in range(100) if floor + 0.01 * k <= 0.95]
        s = max((evaluate(records, subset, th) for th in grid), key=lambda s: s["f1"])
        lines.append(f"| {MODEL_LABELS[model]} | {s['esik']:.2f} | **{s['nadir_bulunan']}/{s['nadir_var']}** | "
                     f"{s['bulunan']}/{s['var']} | {s['p']:.2f} | {s['r']:.2f} | **{s['f1']:.2f}** | "
                     f"{s['uydurma']}/{s['yok']} (%{s['uydurma'] / max(1, s['yok']) * 100:.0f}) |")
    lines += ["", f"Küçük örneklem ({len(ids)} görsel); 2–3 soruluk farklar anlamlı değil."]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "kisa_karsilastirma.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
