"""LVIS ölçüm alt kümesinde (subset_50.json) üç modeli üretim akışıyla ölçer.

Her görselde sorulanlar (LVIS etiketlerine göre):
  var   : görselde etiketli nesneler (gruba girme nedeni olanlar önce, en fazla MAX_POSITIVES)
  yok   : "kesinlikle yok" doğrulanmış nesneler (en fazla MAX_NEGATIVES) → çizilen her kutu yanlıştır
Etiketlenmemiş nesneler sorulmaz (LVIS her nesneyi işaretlemez; bulan model cezalandırılmaz).

Sorgular İngilizce LVIS adlarıyla verilir (english_query): ölçülen tespittir, çeviri değil.
Model en düşük hassasiyet eşiğinde (Geniş) bir kez çalışır, tüm kutular puanlarıyla
outputs/lvis_olcum/tespitler_<model>.json'a yazılır. Sıkı / Dengeli / Geniş ve ileride
denenecek filtreler bu kayıttan modeli yeniden çalıştırmadan hesaplanır.

Puanlama (kategori başına, açgözlü bire bir eşleşme, IoU >= 0.5):
  doğru (TP), yanlış kutu (FP: eşleşmeyen kutu veya "yok" nesneye kutu), kaçırılan (FN)
  precision = TP / (TP + FP), recall = TP / (TP + FN)
  "olmayan nesneye kutu": en az bir kutu çizilen "yok" sorgularının oranı

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.evaluate_subset --model owlvit [--limit 3]
  .venv\\Scripts\\python.exe -m evaluation.lvis.evaluate_subset --report     # kayıtlardan tablo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SUBSET = Path(__file__).with_name("subset_50.json")
LVIS_JSON = ROOT / ".cache" / "lvis" / "lvis_v1_val.json"
IMAGE_DIR = ROOT / ".cache" / "lvis" / "images"
OUT_DIR = ROOT / "outputs" / "lvis_olcum"
QUERY_NAMES = Path(__file__).with_name("query_names.json")
MODELS = ("owlvit", "grounding-dino", "yolo-world")
MODEL_LABELS = {"owlvit": "OWLv2", "grounding-dino": "Grounding DINO", "yolo-world": "YOLO-World",
                "owlv2-large": "OWLv2 large", "llmdet": "LLMDet (base)"}
# Üretimde olmayan, "en iyi yöntem" seçimi için ölçülen adaylar: (eşik politikası, kayıt tabanı).
# Eşikler küçük modellerde kalibre edildi; adayların puan ölçeği farklı olabileceği için
# kayıt daha düşük bir tabandan alınır ve eşik sonradan kayıttan seçilir (candidate_report.py).
CANDIDATES = {"owlv2-large": ("owlv2", 0.05), "llmdet": ("grounding-dino", 0.15)}


def candidate_detector(model: str):
    from backend.app.config import GroundingDinoSettings
    from backend.app.models.grounding_dino_service import GroundingDinoService
    from backend.app.models.owlv2_service import Owlv2Service
    if model == "owlv2-large":
        class Owlv2Large(Owlv2Service):
            model_name = "google/owlv2-large-patch14-ensemble"
        return Owlv2Large()
    if model == "llmdet":
        return GroundingDinoService(GroundingDinoSettings(model_name="iSEE-Laboratory/llmdet_base"))
    raise ValueError(model)
MAX_POSITIVES = 6
MAX_NEGATIVES = 4
IOU_MATCH = 0.5


def query_names(subset: list[dict]) -> dict[str, str]:
    """LVIS kategori adı → modele gidecek okunur İngilizce ad (eş anlamlılardan parantezsiz olan)."""
    needed = {n for item in subset for n in [*item["positives"], *item["negatives"]]}
    result = json.loads(QUERY_NAMES.read_text(encoding="utf-8")) if QUERY_NAMES.exists() else {}
    if needed <= set(result):
        return result
    data = json.loads(LVIS_JSON.read_text(encoding="utf-8"))
    for category in data["categories"]:
        if category["name"] not in needed:
            continue
        synonyms = [category["name"], *category.get("synonyms", [])]
        plain = next((s for s in synonyms if "(" not in s), synonyms[0].split("_(")[0])
        result[category["name"]] = plain.replace("_", " ").strip()
    QUERY_NAMES.write_text(json.dumps(dict(sorted(result.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def questions(item: dict) -> tuple[list[str], list[str]]:
    """Görselde sorulacak 'var' ve 'yok' kategorileri (sabit sıra, tekrarlanabilir)."""
    focus = [c for c in item.get("focus", []) if c in item["positives"]]
    others = [c for c in item["positives"] if c not in focus]
    positives = (focus + others)[:MAX_POSITIVES]
    return positives, item["negatives"][:MAX_NEGATIVES]


def subset_path(tag: str) -> Path:
    return SUBSET if tag == "temel" else Path(__file__).with_name(f"subset_{tag}_50.json")


def detections_path(tag: str, model: str) -> Path:
    # "temel" alt kümenin dosya adları eski haliyle kalır.
    return OUT_DIR / (f"tespitler_{model}.json" if tag == "temel" else f"tespitler_{tag}_{model}.json")


def run_model(model: str, limit: int | None, tag: str = "temel") -> None:
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

    subset = json.loads(subset_path(tag).read_text(encoding="utf-8"))[:limit]
    names = query_names(json.loads(subset_path(tag).read_text(encoding="utf-8")))
    if model in CANDIDATES:
        detector = candidate_detector(model)
        key, floor = CANDIDATES[model]
        policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False)
        if policy.text_threshold is not None:
            policy = dataclasses.replace(policy, text_threshold=floor)
        # Düşük tabanda kutu sayısı sınırları sonucu boşaltmasın; eşik kayıttan sonra uygulanır.
        policy = dataclasses.replace(policy, max_raw_detections=100_000, max_filtered_detections=100_000,
                                     max_duplicate_fraction=1.0)
    else:
        detector = DetectorRegistry().get(model)
        key = detector.policy_key or detector.model_id
        floor = config.SENSITIVITY_THRESHOLDS[key]["loose"]
        policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False)
    translation = TranslationService.__new__(TranslationService)  # english_query verildiği için çeviri yapılmaz
    records = []
    started = time.perf_counter()
    for number, item in enumerate(subset, 1):
        positives, negatives = questions(item)
        asked = positives + negatives
        english = ", ".join(names[c] for c in asked)
        plan = process_query(english, translation, english)
        by_primary = {part["primary_query"]: category for part, category in zip(plan["processed_query_items"], asked)}
        with Image.open(IMAGE_DIR / item["file_name"]) as source:
            image = source.convert("RGB")
        t = time.perf_counter()
        result = run_detection(detector, image, plan, policy)
        records.append({
            "image_id": item["image_id"], "group": item["group"], "positives": positives, "negatives": negatives,
            "seconds": round(time.perf_counter() - t, 2),
            "detections": [{"category": by_primary.get(d["canonical_query"], d["canonical_query"]),
                            "confidence": round(d["confidence"], 4),
                            "box": [round(d["box"][k], 1) for k in ("xmin", "ymin", "xmax", "ymax")]}
                           for d in result["detections"]],
        })
        print(f"[{model}] {number}/{len(subset)} {item['file_name']} {len(asked)} sorgu "
              f"{len(result['detections'])} kutu {records[-1]['seconds']}s", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = detections_path(tag, model)
    target.write_text(json.dumps({"model": model, "floor": floor, "records": records}, indent=1), encoding="utf-8")
    print(f"{target} ({time.perf_counter() - started:.0f} s)")


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def score(records: list[dict], subset: dict[int, dict], keep) -> dict:
    """keep(record, detections) → tutulacak kutular. Sonuç: toplam ve grup bazında sayılar."""
    totals = defaultdict(lambda: defaultdict(int))
    for record in records:
        item = subset[record["image_id"]]
        kept = keep(record, record["detections"])
        for bucket in ("hepsi", record["group"]):
            t = totals[bucket]
            for category in record["positives"]:
                gt = [[x, y, x + w, y + h] for x, y, w, h in item["positives"][category]]
                preds = sorted((d for d in kept if d["category"] == category), key=lambda d: -d["confidence"])
                used = set()
                for d in preds:
                    best, best_i = IOU_MATCH, None
                    for i, g in enumerate(gt):
                        if i not in used and iou(d["box"], g) >= best:
                            best, best_i = iou(d["box"], g), i
                    if best_i is None:
                        t["fp_var"] += 1
                    else:
                        used.add(best_i); t["tp"] += 1
                t["fn"] += len(gt) - len(used)
                t["gt"] += len(gt)
            for category in record["negatives"]:
                boxes = [d for d in kept if d["category"] == category]
                t["fp_yok"] += len(boxes)
                t["yok_sorgu"] += 1
                t["yok_kutulu"] += bool(boxes)
    out = {}
    for bucket, t in totals.items():
        fp = t["fp_var"] + t["fp_yok"]
        p = t["tp"] / (t["tp"] + fp) if t["tp"] + fp else 0.0
        r = t["tp"] / t["gt"] if t["gt"] else 0.0
        out[bucket] = {**t, "precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
                       "yok_oran": t["yok_kutulu"] / t["yok_sorgu"] if t["yok_sorgu"] else 0.0}
    return out


def threshold_filter(threshold: float):
    return lambda record, detections: [d for d in detections if d["confidence"] >= threshold]


def report() -> None:
    sys.path.insert(0, str(ROOT))
    from backend.app import config
    subset = {item["image_id"]: item for item in json.loads(SUBSET.read_text(encoding="utf-8"))}
    keys = {"owlvit": "owlv2", "grounding-dino": "grounding-dino", "yolo-world": "yolo-world"}
    lines = ["# LVIS alt kümesi (50 görsel) · temel ölçüm", "",
             f"Her görselde en fazla {MAX_POSITIVES} 'var' ve {MAX_NEGATIVES} 'yok' sorgusu; IoU >= {IOU_MATCH} eşleşme.",
             "Yanlış kutu = eşleşmeyen kutu + olmayan nesneye çizilen kutu.", "",
             "| Model | Hassasiyet | Eşik | Doğru | Yanlış kutu | Kaçırılan | Precision | Recall | F1 | Olmayan nesneye kutu |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    group_rows = []
    for model in MODELS:
        path = OUT_DIR / f"tespitler_{model}.json"
        if not path.exists():
            lines.append(f"| {MODEL_LABELS[model]} | — | — | ölçülmedi | | | | | | |")
            continue
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        key = keys[model]
        levels = {"Sıkı": config.SENSITIVITY_THRESHOLDS[key]["strict"],
                  "Dengeli": config.ADAPTIVE_THRESHOLDS[key].thresholds[0],
                  "Geniş": config.SENSITIVITY_THRESHOLDS[key]["loose"]}
        for level, threshold in levels.items():
            s = score(records, subset, threshold_filter(threshold))
            a = s["hepsi"]
            lines.append(f"| {MODEL_LABELS[model]} | {level} | {threshold:.2f} | {a['tp']} | {a['fp_var'] + a['fp_yok']} | "
                         f"{a['fn']} | {a['precision']:.2f} | {a['recall']:.2f} | {a['f1']:.2f} | "
                         f"{a['yok_kutulu']}/{a['yok_sorgu']} (%{a['yok_oran'] * 100:.0f}) |")
            if level == "Dengeli":
                group_rows.append((MODEL_LABELS[model], s))
    if group_rows:
        groups = ["masa", "envanter", "guvenlik", "kucuk", "benzer"]
        lines += ["", "## Gruplara göre (Dengeli) · F1 / olmayan nesneye kutu oranı", "",
                  "| Model | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
        for label, s in group_rows:
            cells = [f"{s[g]['f1']:.2f} / %{s[g]['yok_oran'] * 100:.0f}" if g in s else "—" for g in groups]
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / "temel_olcum.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nRapor: {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=(*MODELS, *CANDIDATES))
    parser.add_argument("--limit", type=int, default=None, help="yalnızca ilk N görsel (deneme)")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--subset", default="temel", help="temel (subset_50.json) veya nadir (subset_nadir_50.json)")
    args = parser.parse_args()
    if args.model:
        run_model(args.model, args.limit, args.subset)
    if args.report:
        report()


if __name__ == "__main__":
    main()
