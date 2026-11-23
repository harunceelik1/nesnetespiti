r"""Kullanıcının kendi masa fotoğraflarında (gerçek kullanım) modelleri ölçer.

Cevap anahtarı: evaluation/masa/etiketler.json (5 fotoğraf, elle işaretlenmiş kutular).
Her fotoğrafta listedeki 14 nesnenin hepsi + 5 ek "yok" nesnesi sorulur; görselde
olmayan her nesne "yok" sorusudur (çizilen kutu uydurmadır).
Model en düşük tabanda bir kez çalışır, kutular kaydedilir; eşik sonradan uygulanır:
  her model kendi en iyi eşiğinde değerlendirilir (adayların kalibre eşiği yok).
Eşleşme: IoU >= 0.5 (LVIS ölçümüyle aynı).

Kullanım (proje kökünden):
  .venv\Scripts\python.exe -m evaluation.masa.evaluate_masa --model owlv2-large
  .venv\Scripts\python.exe -m evaluation.masa.evaluate_masa --report
"""

from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from pathlib import Path

from evaluation.lvis.evaluate_subset import CANDIDATES, MODEL_LABELS, MODELS, OUT_DIR as LVIS_OUT, baseline_detector, candidate_detector, iou

HERE = Path(__file__).resolve().parent
LABELS = json.loads((HERE / "etiketler.json").read_text(encoding="utf-8"))
PHOTO_DIR = Path(os.environ.get("MASA_FOTO_DIZINI", Path.home() / "Desktop" / "gorseller"))
OUT_DIR = LVIS_OUT.parent / "masa_olcum"
QUERIES = [*LABELS["nesneler"], *LABELS["ek_yok"]]
ALL = (*MODELS, *CANDIDATES)


def run(model: str) -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    import dataclasses
    from PIL import Image
    from backend.app import config
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService

    if model in CANDIDATES:
        detector = candidate_detector(model)
        key, floor = CANDIDATES[model]
    else:
        detector = baseline_detector(model)
        key = detector.policy_key or detector.model_id
        floor = config.SENSITIVITY_THRESHOLDS[key]["loose"]
    policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False,
                                 max_raw_detections=100_000, max_filtered_detections=100_000, max_duplicate_fraction=1.0)
    if policy.text_threshold is not None and model in CANDIDATES:
        policy = dataclasses.replace(policy, text_threshold=floor)
    translation = TranslationService.__new__(TranslationService)
    english = ", ".join(QUERIES)
    plan = process_query(english, translation, english)
    by_primary = {part["primary_query"]: q for part, q in zip(plan["processed_query_items"], QUERIES)}
    records = []
    for name in LABELS["gorseller"]:
        with Image.open(PHOTO_DIR / name) as source:
            image = source.convert("RGB")
        t = time.perf_counter()
        result = run_detection(detector, image, plan, policy)
        records.append({"image": name, "seconds": round(time.perf_counter() - t, 1), "detections": [
            {"category": by_primary.get(d["canonical_query"], d["canonical_query"]), "confidence": round(d["confidence"], 4),
             "box": [round(d["box"][k], 1) for k in ("xmin", "ymin", "xmax", "ymax")]} for d in result["detections"]]})
        print(f"[{model}] {name} {len(result['detections'])} kutu {records[-1]['seconds']}s", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"tespitler_{model}.json").write_text(json.dumps({"model": model, "floor": floor, "records": records}, indent=1),
                                                    encoding="utf-8")


def score(model: str, threshold: float) -> dict:
    data = json.loads((OUT_DIR / f"tespitler_{model}.json").read_text(encoding="utf-8"))
    t = {"tp": 0, "fp": 0, "gt": 0, "var": 0, "bulunan": 0, "yok": 0, "uydurma": 0, "kacan": []}
    for record in data["records"]:
        truth = LABELS["gorseller"][record["image"]]
        kept = [d for d in record["detections"] if d["confidence"] >= threshold]
        for query in QUERIES:
            boxes = sorted((d for d in kept if d["category"] == query), key=lambda d: -d["confidence"])
            if query not in truth:
                t["yok"] += 1; t["uydurma"] += bool(boxes); t["fp"] += len(boxes)
                continue
            gt, used = truth[query], set()
            for d in boxes:
                best, best_i = 0.5, None
                for i, g in enumerate(gt):
                    if i not in used and iou(d["box"], g) >= best:
                        best, best_i = iou(d["box"], g), i
                if best_i is None:
                    t["fp"] += 1
                else:
                    used.add(best_i); t["tp"] += 1
            t["gt"] += len(gt); t["var"] += 1; t["bulunan"] += bool(used)
            if not used:
                t["kacan"].append(f"{query} ({record['image']})")
    p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
    r = t["tp"] / t["gt"] if t["gt"] else 0.0
    return {**t, "p": p, "r": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def report() -> None:
    lines = ["# Kullanıcının masa fotoğrafları (5 fotoğraf, 45 nesne, elle işaretli)", "",
             "Her fotoğrafta 19 nesne soruldu; görselde olmayanlar 'yok' sorusu. IoU >= 0.5.",
             "Her model kendi en iyi eşiğinde (bu fotoğraflarda F1'i en yüksek eşik); aynı iyimser muamele.", "",
             "| Model | En iyi eşik | Bulunan nesne | Precision | Recall | F1 | Olmayan nesneye kutu | Bulunamayanlar |",
             "|---|---|---|---|---|---|---|---|"]
    for model in ALL:
        path = OUT_DIR / f"tespitler_{model}.json"
        if not path.exists():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        floor = min((d["confidence"] for r in records for d in r["detections"]), default=0.0)
        grid = [round(floor + 0.01 * k, 2) for k in range(100) if floor + 0.01 * k <= 0.95]
        threshold, s = max(((th, score(model, th)) for th in grid), key=lambda x: x[1]["f1"])
        missed = ", ".join(sorted({m.split(" (")[0] for m in s["kacan"]}))
        lines.append(f"| {MODEL_LABELS[model]} | {threshold:.2f} | {s['bulunan']}/{s['var']} | {s['p']:.2f} | {s['r']:.2f} | "
                     f"**{s['f1']:.2f}** | {s['uydurma']}/{s['yok']} (%{s['uydurma'] / s['yok'] * 100:.0f}) | {missed or '—'} |")
    lines += ["", "Küçük örneklem: tek bir masa, 5 fotoğraf. LVIS ölçümünü tamamlar, yerine geçmez."]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "masa_olcum.md").write_text(text, encoding="utf-8")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=ALL, action="append")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    for model in args.model or []:
        run(model)
    if args.report:
        report()


if __name__ == "__main__":
    main()
