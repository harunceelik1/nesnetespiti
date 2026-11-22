"""Göreli puan filtresi deneyi (modeller yeniden çalıştırılmaz; kayıtlı kutular kullanılır).

Kural: aynı görselde aynı sorgunun kutuları arasında, en yüksek puanlı kutunun
`oran` katından düşük puanlı kutular atılır. Önce modelin Dengeli eşiği uygulanır.
  ör. en iyi kutu 0.44, oran 0.5 → 0.22 altındaki kutular gider (saç spreyi: 0.19'luk iki kutu).
Not: Filtre her sorguda en iyi kutuyu korur; bu yüzden "olmayan nesneye kutu" oranını
düşüremez, yalnızca ikincil kutuları azaltır. Çok kopyalı sahnelerde (envanter) doğru
kutuları da atma riski vardır; grup tablosu bunu gösterir.

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.relative_filter
"""

from __future__ import annotations

import json
from collections import defaultdict

from backend.app import config
from evaluation.lvis.evaluate_subset import MODEL_LABELS, MODELS, OUT_DIR, SUBSET, score

RATIOS = (0.3, 0.4, 0.5, 0.6, 0.7)
GROUPS = ("masa", "envanter", "guvenlik", "kucuk", "benzer")
POLICY_KEYS = {"owlvit": "owlv2", "grounding-dino": "grounding-dino", "yolo-world": "yolo-world"}


def relative_filter(threshold: float, ratio: float | None):
    def keep(record, detections):
        kept = [d for d in detections if d["confidence"] >= threshold]
        if ratio is None:
            return kept
        best = defaultdict(float)
        for d in kept:
            best[d["category"]] = max(best[d["category"]], d["confidence"])
        return [d for d in kept if d["confidence"] >= ratio * best[d["category"]]]
    return keep


def main() -> None:
    subset = {item["image_id"]: item for item in json.loads(SUBSET.read_text(encoding="utf-8"))}
    lines = ["# Göreli puan filtresi · LVIS 50 görsel (Dengeli eşik üstüne)", "",
             "Kural: aynı görselde aynı sorgunun en iyi kutusunun `oran` katından düşük puanlı kutular atılır.", "",
             "| Model | Oran | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 | Olmayan nesneye kutu |",
             "|---|---|---|---|---|---|---|---|---|"]
    group_lines = ["", "## Gruplara göre F1 (filtresiz → oran 0.5)", "",
                   "| Model | " + " | ".join(GROUPS) + " |", "|---|" + "---|" * len(GROUPS)]
    for model in MODELS:
        path = OUT_DIR / f"tespitler_{model}.json"
        if not path.exists():
            lines.append(f"| {MODEL_LABELS[model]} | — | henüz ölçülmedi | | | | | | |")
            continue
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        threshold = config.ADAPTIVE_THRESHOLDS[POLICY_KEYS[model]].thresholds[0]
        results = {}
        for ratio in (None, *RATIOS):
            s = score(records, subset, relative_filter(threshold, ratio))
            results[ratio] = s
            a = s["hepsi"]
            label = "filtresiz" if ratio is None else f"{ratio:.1f}"
            lines.append(f"| {MODEL_LABELS[model]} | {label} | {a['tp']} | {a['fp_var'] + a['fp_yok']} | {a['fn']} | "
                         f"{a['precision']:.2f} | {a['recall']:.2f} | {a['f1']:.2f} | %{a['yok_oran'] * 100:.0f} |")
        cells = [f"{results[None][g]['f1']:.2f} → {results[0.5][g]['f1']:.2f}" for g in GROUPS]
        group_lines.append(f"| {MODEL_LABELS[model]} | " + " | ".join(cells) + " |")
    text = "\n".join(lines + group_lines) + "\n"
    target = OUT_DIR / "goreli_filtre.md"
    target.write_text(text, encoding="utf-8")
    print(text)
    print(f"Rapor: {target}")


if __name__ == "__main__":
    main()
