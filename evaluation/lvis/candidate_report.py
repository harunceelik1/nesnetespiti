r"""Tek yöntem seçimi: aday modellerin sık ve nadir LVIS nesnelerindeki başarısı.

Adayların eşiği küçük modellerde kalibre edilmediği için her model için eşik, yalnızca
**temel** alt kümede (çoğu sık nesne) F1'i en yüksek yapan değer olarak seçilir; nadir
küme eşik seçiminde kullanılmaz. Sonra aynı eşikle sık / ara / nadir tablo çıkarılır.
Üretimdeki modeller (OWLv2 base, Grounding DINO tiny) ayrıca kalibre edilmiş Dengeli
eşikleriyle de gösterilir.

Kullanım (proje kökünden, kayıtlar evaluate_subset ile üretildikten sonra):
  .venv\Scripts\python.exe -m evaluation.lvis.candidate_report
"""

from __future__ import annotations

import json

from backend.app import config
from evaluation.lvis.evaluate_subset import (CANDIDATES, MODEL_LABELS, OUT_DIR, detections_path, score,
                                             subset_path, threshold_filter)
from evaluation.lvis.frequency_report import POLICY_KEYS, collect

MODELS = ("owlvit", "owlv2-large", "grounding-dino", "llmdet", "yolo-world")


def floor(model: str) -> float:
    if model in CANDIDATES:
        return CANDIDATES[model][1]
    return config.SENSITIVITY_THRESHOLDS[POLICY_KEYS[model]]["loose"]


def best_threshold(model: str) -> tuple[float, float]:
    """Temel kümede F1'i en yüksek eşik (0.01 adım)."""
    records = json.loads(detections_path("temel", model).read_text(encoding="utf-8"))["records"]
    subset = {i["image_id"]: i for i in json.loads(subset_path("temel").read_text(encoding="utf-8"))}
    grid = [round(floor(model) + 0.01 * k, 2) for k in range(0, 80)]
    scored = [(score(records, subset, threshold_filter(t))["hepsi"]["f1"], t) for t in grid if t <= 0.9]
    f1, threshold = max(scored)
    return threshold, f1


def row(label: str, threshold: float, totals: dict) -> tuple[str, dict]:
    cells, f1s = [], {}
    for key in ("f", "c", "r"):
        t = totals[key]
        p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
        r = t["tp"] / t["gt"] if t["gt"] else 0.0
        f1s[key] = 2 * p * r / (p + r) if p + r else 0.0
        f1s[key + "_found"] = t["bulunan_soru"] / t["var_soru"] if t["var_soru"] else 0.0
        f1s[key + "_fake"] = t["yok_kutulu"] / t["yok_soru"] if t["yok_soru"] else 0.0
    drop = (1 - f1s["r"] / f1s["f"]) * 100 if f1s["f"] else 0.0
    fake = (sum(totals[k]["yok_kutulu"] for k in "fcr") / max(1, sum(totals[k]["yok_soru"] for k in "fcr")))
    return (f"| {label} | {threshold:.2f} | {f1s['f']:.2f} | {f1s['c']:.2f} | **{f1s['r']:.2f}** | %{drop:.0f} | "
            f"%{f1s['r_found'] * 100:.0f} | %{fake * 100:.0f} |"), f1s


def main() -> None:
    lines = ["# Tek yöntem seçimi: sık / ara / nadir LVIS nesneleri", "",
             "Eşik: her model için yalnızca temel kümede (çoğu sık nesne) F1'i en yüksek yapan değer; nadir küme",
             "eşik seçiminde kullanılmadı. Üretimdeki iki model kalibre Dengeli eşikle de verildi.", "",
             "| Model | Eşik | Sık F1 | Ara F1 | Nadir F1 | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |",
             "|---|---|---|---|---|---|---|---|"]
    for model in MODELS:
        if not detections_path("temel", model).exists() or not detections_path("nadir", model).exists():
            lines.append(f"| {MODEL_LABELS[model]} | — | ölçülmedi | | | | | |")
            continue
        threshold, _ = best_threshold(model)
        lines.append(row(MODEL_LABELS[model], threshold, collect(model, threshold))[0])
        if model in POLICY_KEYS and model != "yolo-world":
            calibrated = config.ADAPTIVE_THRESHOLDS[POLICY_KEYS[model]].thresholds[0]
            lines.append(row(MODEL_LABELS[model] + " (Dengeli)", calibrated, collect(model, calibrated))[0])
    lines += ["", "Nadir 'var' sorusu 51 tane; iki nokta altı farklar anlamlı sayılmamalı."]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "yontem_secimi.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
