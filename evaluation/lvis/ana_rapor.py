"""Ödevin ana tablosu: ana LVIS kümesinde (subset_ana.json, 345 görsel) sık / ara / nadir başarı.

Küme: temel 50 görsel + LVIS v1 val'deki tam etiketli nadir (r) nesne havuzunun tamamı (select_main.py).
Her soru, sorulan kategorinin LVIS sıklık sınıfına göre ayrılır:
  f (frequent) > 100 eğitim görseli · c (common) 11–100 · r (rare) <= 10 → "görülmemiş nesne" ölçütü.
"Var" soruları: doğru / yanlış kutu / kaçırılan → precision, recall, F1 (IoU >= 0.5, açgözlü bire bir eşleşme).
"Yok" soruları: olmayan nesneye kutu çizilen soruların oranı (uydurma kutu).
Eşik: her modelin Dengeli eşiği (uygulamanın varsayılanı, config.ADAPTIVE_THRESHOLDS).
Belirsizlik: görsellerin yeniden örneklenmesiyle (bootstrap, 2000 tekrar, sabit tohum) %95 aralık.

Önce kayıtlar: .venv\\Scripts\\python.exe -m evaluation.lvis.evaluate_subset --model <model> --subset ana
Rapor (proje kökünden): .venv\\Scripts\\python.exe -m evaluation.lvis.ana_rapor
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from backend.app import config
from evaluation.lvis.evaluate_subset import IOU_MATCH, OUT_DIR, detections_path, iou, subset_path

TAG = "ana"
FREQUENCY = json.loads(Path(__file__).with_name("category_frequency.json").read_text(encoding="utf-8"))
# (kayıt adı, tablo adı, eşik politikası anahtarı). Ölçüm kayıtlarında "owlvit" = OWLv2 base.
MODELS = (("owlv2-large", "**OWLv2 large (uygulama)**", "owlv2-large"),
          ("owlvit", "OWLv2 base", "owlv2"),
          ("grounding-dino", "Grounding DINO tiny", "grounding-dino"),
          ("yolo-world", "YOLO-World s", "yolo-world"))
BUCKETS = (("f", "Sık (f)"), ("c", "Ara (c)"), ("r", "Nadir (r)"))
FIELDS = ("tp", "fp", "gt", "var_soru", "bulunan_soru", "yok_soru", "yok_kutulu")
BOOTSTRAP = 2000
SEED = 7


def per_image(record: dict, item: dict, threshold: float) -> dict[str, dict[str, int]]:
    """Bir görselin sıklık sınıfı başına sayıları."""
    counts = {key: dict.fromkeys(FIELDS, 0) for key, _ in BUCKETS}
    kept = [d for d in record["detections"] if d["confidence"] >= threshold]
    for category in record["positives"]:
        t = counts[FREQUENCY[category]]
        gt = [[x, y, x + w, y + h] for x, y, w, h in item["positives"][category]]
        used = set()
        for d in sorted((d for d in kept if d["category"] == category), key=lambda d: -d["confidence"]):
            best, best_i = IOU_MATCH, None
            for i, g in enumerate(gt):
                if i not in used and iou(d["box"], g) >= best:
                    best, best_i = iou(d["box"], g), i
            if best_i is None:
                t["fp"] += 1
            else:
                used.add(best_i); t["tp"] += 1
        t["gt"] += len(gt); t["var_soru"] += 1; t["bulunan_soru"] += bool(used)
    for category in record["negatives"]:
        t = counts[FREQUENCY[category]]
        t["yok_soru"] += 1
        t["yok_kutulu"] += any(d["category"] == category for d in kept)
    return counts


def total(images: list[dict], key: str) -> dict[str, int]:
    return {f: sum(img[key][f] for img in images) for f in FIELDS}


def f1(t: dict) -> float:
    p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
    r = t["tp"] / t["gt"] if t["gt"] else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def interval(images: list[dict], key: str) -> tuple[float, float]:
    rng = random.Random(SEED)
    values = sorted(f1(total([rng.choice(images) for _ in images], key)) for _ in range(BOOTSTRAP))
    return values[int(0.025 * BOOTSTRAP)], values[int(0.975 * BOOTSTRAP) - 1]


def pct(a: int, b: int) -> str:
    return f"%{a / b * 100:.0f}" if b else "—"


def main() -> None:
    subset = {i["image_id"]: i for i in json.loads(subset_path(TAG).read_text(encoding="utf-8"))}
    rare_cats = {c for i in subset.values() for c in i["positives"] if FREQUENCY[c] == "r"}
    lines = [f"# Ana ölçüm: LVIS v1 val, {len(subset)} görsel (sık / ara / nadir)", "",
             f"Küme: temel 50 görsel + tam etiketli nadir nesne içeren görsellerin tamamı ({len(rare_cats)} farklı nadir nesne).",
             "LVIS sıklık sınıfı: f > 100 eğitim görseli, c 11–100, **r ≤ 10 (görülmemiş nesne ölçütü)**. IoU ≥ 0.5.",
             "Eşik: her modelin Dengeli eşiği (uygulamanın varsayılanı). Köşeli parantez: görsel bazında bootstrap %95 aralığı.", "",
             "## Özet", "",
             "| Model | Eşik | Sık F1 | Nadir F1 [%95 aralık] | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |",
             "|---|---|---|---|---|---|---|"]
    detail = ["", "## Ayrıntı", "",
              "| Model | Sınıf | 'Var' sorusu | Nesneyi en az bir kez bulduğu | Precision | Recall | F1 | 'Yok' sorusu | Uydurma kutu |",
              "|---|---|---|---|---|---|---|---|---|"]
    for model, label, key in MODELS:
        path = detections_path(TAG, model)
        if not path.exists():
            lines.append(f"| {label} | — | ölçülmedi | | | | |")
            continue
        threshold = config.ADAPTIVE_THRESHOLDS[key].thresholds[0]
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        images = [per_image(r, subset[r["image_id"]], threshold) for r in records]
        sums = {k: total(images, k) for k, _ in BUCKETS}
        f_f1, r_f1 = f1(sums["f"]), f1(sums["r"])
        low, high = interval(images, "r")
        yok = sum(s["yok_kutulu"] for s in sums.values()), sum(s["yok_soru"] for s in sums.values())
        drop = f"%{(1 - r_f1 / f_f1) * 100:.0f}" if f_f1 else "—"
        lines.append(f"| {label} | {threshold:.2f} | {f_f1:.2f} | **{r_f1:.2f}** [{low:.2f}–{high:.2f}] | {drop} | "
                     f"{sums['r']['bulunan_soru']}/{sums['r']['var_soru']} ({pct(sums['r']['bulunan_soru'], sums['r']['var_soru'])}) | "
                     f"{pct(*yok)} |")
        for k, bucket in BUCKETS:
            t = sums[k]
            p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
            r = t["tp"] / t["gt"] if t["gt"] else 0.0
            detail.append(f"| {label} | {bucket} | {t['var_soru']} | {t['bulunan_soru']} ({pct(t['bulunan_soru'], t['var_soru'])}) | "
                          f"{p:.2f} | {r:.2f} | {f1(t):.2f} | {t['yok_soru']} | {pct(t['yok_kutulu'], t['yok_soru'])} |")
    lines += detail
    lines += ["", "Eski 50'lik kümelerin sonuçları (temel_olcum.md, siklik_karsilastirma.md, yontem_secimi.md) korunur;",
              "bu tablo onların yerine ana ölçüttür."]
    text = "\n".join(lines) + "\n"
    target = OUT_DIR / "ana_olcum.md"
    target.write_text(text, encoding="utf-8")
    print(text)
    print(f"Rapor: {target}")


if __name__ == "__main__":
    main()
