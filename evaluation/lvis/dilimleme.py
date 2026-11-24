r"""Dilimleme denemesinin LVIS nadir kümesindeki doğrulaması (OWLv2 large).

Masa fotoğraflarında (evaluation/masa/dilimleme.py) seçilen kural burada DEĞİŞTİRİLMEDEN
sınanır: 2×2 dilim, %25 örtüşme; dilim kutusu yalnızca puanı >= 0.30, nesneyi kesen bir dilim
kenarına değmiyor ve görselin <= %1'i ise eklenir. Eşik masada seçildiği için asıl test budur.

Tam görsel kutuları kayıtlı (tespitler_nadir_owlv2-large.json, taban 0.05); yalnızca dilimler
çalışır. Kayıt her görselden sonra yazılır; yarıda kalırsa kaldığı yerden devam eder.

Kullanım (proje kökünden):
  .venv\Scripts\python.exe -m evaluation.lvis.dilimleme --run      # ~2 dk/görsel, 50 görsel
  .venv\Scripts\python.exe -m evaluation.lvis.dilimleme --report
"""

from __future__ import annotations

import argparse
import json
import time

from evaluation.lvis.evaluate_subset import IMAGE_DIR, OUT_DIR, detections_path, query_names, questions, subset_path
from evaluation.masa.dilimleme import _nms, _touches_cut, tiles

MODEL = "owlv2-large"
TAG = "nadir"
TILE_FILE = OUT_DIR / f"dilimler_{TAG}_{MODEL}.json"
TILE_THRESHOLD = 0.30   # masada seçildi
MAX_AREA = 0.01         # masada seçildi


def run() -> None:
    import dataclasses
    import os
    import warnings
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    from PIL import Image
    from backend.app import config
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService
    from evaluation.lvis.evaluate_subset import CANDIDATES, candidate_detector

    subset = json.loads(subset_path(TAG).read_text(encoding="utf-8"))
    names = query_names(subset)
    records = json.loads(TILE_FILE.read_text(encoding="utf-8"))["records"] if TILE_FILE.exists() else []
    done = {r["image_id"] for r in records}
    detector = candidate_detector(MODEL)
    key, floor = CANDIDATES[MODEL]
    # evaluate_subset.run_model ile aynı aday politikası.
    policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False,
                                 max_raw_detections=100_000, max_filtered_detections=100_000, max_duplicate_fraction=1.0)
    translation = TranslationService.__new__(TranslationService)
    started = time.perf_counter()
    for number, item in enumerate(subset, 1):
        if item["image_id"] in done:
            continue
        positives, negatives = questions(item)
        asked = positives + negatives
        english = ", ".join(names[c] for c in asked)
        plan = process_query(english, translation, english)
        by_primary = {part["primary_query"]: c for part, c in zip(plan["processed_query_items"], asked)}
        with Image.open(IMAGE_DIR / item["file_name"]) as source:
            image = source.convert("RGB")
        t = time.perf_counter()
        for index, (x0, y0, x1, y1) in enumerate(tiles(*image.size)):
            result = run_detection(detector, image.crop((x0, y0, x1, y1)), plan, policy)
            records.append({"image_id": item["image_id"], "size": list(image.size), "tile": index, "rect": [x0, y0, x1, y1],
                            "detections": [
                {"category": by_primary.get(d["canonical_query"], d["canonical_query"]), "confidence": round(d["confidence"], 4),
                 "box": [round(d["box"]["xmin"] + x0, 1), round(d["box"]["ymin"] + y0, 1),
                         round(d["box"]["xmax"] + x0, 1), round(d["box"]["ymax"] + y0, 1)]}
                for d in result["detections"]]})
        TILE_FILE.write_text(json.dumps({"model": MODEL, "floor": floor, "records": records}, indent=1), encoding="utf-8")
        elapsed = time.perf_counter() - started
        print(f"{number}/{len(subset)} {item['file_name']} {time.perf_counter() - t:.0f}s (toplam {elapsed / 60:.0f} dk)", flush=True)


def variants() -> dict[str, list[dict]]:
    full = json.loads(detections_path(TAG, MODEL).read_text(encoding="utf-8"))["records"]
    tile_records = json.loads(TILE_FILE.read_text(encoding="utf-8"))["records"]
    by_image: dict[int, list] = {}
    for r in tile_records:
        by_image.setdefault(r["image_id"], []).extend((r["rect"], r["size"], d) for d in r["detections"])
    full = [r for r in full if r["image_id"] in by_image]  # yarım çalıştırmada aynı görseller karşılaştırılır

    def build(keep) -> list[dict]:
        return [{**r, "detections": _nms([*r["detections"], *(d for rect, size, d in by_image[r["image_id"]]
                                                                 if keep(d, rect, size))])} for r in full]

    def small(d, size, area=MAX_AREA):
        return (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) <= area * size[0] * size[1]

    out = {
        "Tam görsel (mevcut)": full,
        "Tam + dilimler (NMS)": build(lambda d, rect, size: True),
        "Tam + dilimler, kesik kutular atılır": build(lambda d, rect, size: not _touches_cut(d["box"], rect, size)),
        f"**Masada seçilen kural** (dilim eşiği {TILE_THRESHOLD}, alan <= %{MAX_AREA * 100:.0f})": build(
            lambda d, rect, size: d["confidence"] >= TILE_THRESHOLD and not _touches_cut(d["box"], rect, size) and small(d, size)),
    }
    # Bilgi amaçlı: kuralın LVIS'te ayarlanmış halleri (aynı veride seçim olur, kanıt sayılmaz).
    for tt in (0.20, 0.25, 0.35, 0.40):
        out[f"(ayar) dilim eşiği {tt}, alan <= %1"] = build(
            lambda d, rect, size, tt=tt: d["confidence"] >= tt and not _touches_cut(d["box"], rect, size) and small(d, size))
    out["(ayar) dilim eşiği 0.30, alan sınırı yok"] = build(
        lambda d, rect, size: d["confidence"] >= TILE_THRESHOLD and not _touches_cut(d["box"], rect, size))
    return out


def report() -> None:
    from evaluation.lvis.candidate_report import row
    from evaluation.lvis.frequency_report import collect
    vs = variants()
    count = len(next(iter(vs.values())))
    lines = ["# Dilimleme doğrulaması: LVIS nadir kümesi, OWLv2 large", "",
             f"{count} görsel (çoğu 640×480). 2×2 dilim, %25 örtüşme; tam görsel + 4 dilim = 5 forward.",
             "Eşik 0.14 = temel kümede F1'i en yüksek eşik (yontem_secimi.md ile aynı); 0.17 = Sıkı.",
             "Sık / ara / nadir: yalnızca bu kümede sorulan nesneler. IoU >= 0.5.", ""]
    for threshold in (0.14, 0.17):
        lines += [f"## Tam görsel eşiği {threshold}", "",
                  "| Yöntem | Eşik | Sık F1 | Ara F1 | Nadir F1 | Sık→nadir düşüş | Nadir nesneyi bulduğu soru | Olmayan nesneye kutu |",
                  "|---|---|---|---|---|---|---|---|"]
        for label, records in vs.items():
            lines.append(row(label, threshold, collect(MODEL, threshold, {TAG: records}))[0])
        lines.append("")
    lines += ["Nadir 'var' sorusu 51 tane; iki nokta altı farklar anlamlı sayılmamalı.",
              "'(ayar)' satırları LVIS'te ayarlanmıştır, kanıt değil bilgi içindir."]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "dilimleme_nadir.md").write_text(text, encoding="utf-8")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.run:
        run()
    if args.report:
        report()


if __name__ == "__main__":
    main()
