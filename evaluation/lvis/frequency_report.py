"""Ödevin ana tablosu: sık (f) / ara (c) / nadir (r) LVIS kategorilerinde üç modelin başarısı.

İki alt kümenin (temel: subset_50.json, nadir: subset_nadir_50.json) kayıtlı tespitleri
birlikte kullanılır; her soru, sorulan kategorinin LVIS sıklık sınıfına göre ayrılır:
  f (frequent) > 100 eğitim görseli · c (common) 11–100 · r (rare) <= 10  → "görülmemiş nesne" ölçütü.
"Var" soruları: doğru / yanlış kutu / kaçırılan, precision, recall, F1 (IoU >= 0.5).
"Yok" soruları: olmayan nesneye kutu çizilen soruların oranı (uydurma kutu).
Eşik: modelin Dengeli eşiği (uygulamanın varsayılanı).

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.frequency_report
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from backend.app import config
from evaluation.lvis.evaluate_subset import MODEL_LABELS, MODELS, OUT_DIR, detections_path, iou, subset_path

FREQUENCY = json.loads(Path(__file__).with_name("category_frequency.json").read_text(encoding="utf-8"))
POLICY_KEYS = {"owlvit": "owlv2", "grounding-dino": "grounding-dino", "yolo-world": "yolo-world"}
BUCKETS = (("f", "Sık (f)"), ("c", "Ara (c)"), ("r", "Nadir (r)"))


def collect(model: str) -> dict | None:
    threshold = config.ADAPTIVE_THRESHOLDS[POLICY_KEYS[model]].thresholds[0]
    totals = defaultdict(lambda: defaultdict(int))
    found_any = False
    for tag in ("temel", "nadir"):
        path = detections_path(tag, model)
        if not path.exists():
            continue
        found_any = True
        subset = {i["image_id"]: i for i in json.loads(subset_path(tag).read_text(encoding="utf-8"))}
        for record in json.loads(path.read_text(encoding="utf-8"))["records"]:
            item = subset[record["image_id"]]
            kept = [d for d in record["detections"] if d["confidence"] >= threshold]
            for category in record["positives"]:
                t = totals[FREQUENCY[category]]
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
                t["gt"] += len(gt); t["var_soru"] += 1
                t["bulunan_soru"] += bool(used)
            for category in record["negatives"]:
                t = totals[FREQUENCY[category]]
                t["yok_soru"] += 1
                t["yok_kutulu"] += any(d["category"] == category for d in kept)
    return totals if found_any else None


def ratio(a: int, b: int) -> float:
    return a / b if b else 0.0


def main() -> None:
    lines = ["# Sık / ara / nadir LVIS kategorilerinde üç model (Dengeli eşik)", "",
             "LVIS sıklık sınıfı: f > 100 eğitim görseli, c 11–100, **r ≤ 10 (görülmemiş nesne ölçütü)**.",
             "İki alt küme birlikte: temel (50 görsel, çoğu sık nesne) + nadir (50 görsel, 50 farklı nadir nesne).", "",
             "| Model | Sınıf | 'Var' sorusu | Nesneyi en az bir kez bulduğu soru | Precision | Recall | F1 | 'Yok' sorusu | Uydurma kutu |",
             "|---|---|---|---|---|---|---|---|---|"]
    summary = []
    for model in MODELS:
        totals = collect(model)
        if totals is None:
            lines.append(f"| {MODEL_LABELS[model]} | — | ölçülmedi | | | | | | |")
            continue
        f1s = {}
        for key, label in BUCKETS:
            t = totals[key]
            p, r = ratio(t["tp"], t["tp"] + t["fp"]), ratio(t["tp"], t["gt"])
            f1 = 2 * p * r / (p + r) if p + r else 0.0
            f1s[key] = f1
            lines.append(f"| {MODEL_LABELS[model]} | {label} | {t['var_soru']} | {t['bulunan_soru']} "
                         f"(%{ratio(t['bulunan_soru'], t['var_soru']) * 100:.0f}) | {p:.2f} | {r:.2f} | {f1:.2f} | "
                         f"{t['yok_soru']} | %{ratio(t['yok_kutulu'], t['yok_soru']) * 100:.0f} |")
        summary.append((MODEL_LABELS[model], f1s))
    if summary:
        lines += ["", "## Özet: sık nesneden nadir nesneye F1 düşüşü", "",
                  "| Model | Sık F1 | Nadir F1 | Düşüş |", "|---|---|---|---|"]
        for label, f1s in summary:
            drop = (1 - f1s["r"] / f1s["f"]) * 100 if f1s["f"] else 0.0
            lines.append(f"| {label} | {f1s['f']:.2f} | {f1s['r']:.2f} | %{drop:.0f} |")
    lines += ["", "Not: nadir 'var' sorusu sayısı küçüktür (~50); yüzdeler birkaç soruyla değişebilir."]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "siklik_karsilastirma.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
