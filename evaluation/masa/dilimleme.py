r"""Dilimleme (SAHI benzeri) denemesi: küçük nesneler için görseli örtüşen dilimlere bölüp
OWLv2 large'ı her dilimde ayrıca çalıştırır.

Tam görsel kutuları zaten kayıtlı (outputs/masa_olcum/tespitler_owlv2-large.json, taban 0.05);
burada yalnızca dilimler çalışır ve kutular orijinal koordinatlara kaydırılarak saklanır.
Birleştirme yöntemleri sonradan, modeli yeniden çalıştırmadan karşılaştırılır.

Kullanım (proje kökünden):
  .venv\Scripts\python.exe -m evaluation.masa.dilimleme --run      # ~2 dk/görsel
  .venv\Scripts\python.exe -m evaluation.masa.dilimleme --report
"""

from __future__ import annotations

import argparse
import json
import time

from evaluation.lvis.evaluate_subset import iou
from evaluation.masa.evaluate_masa import LABELS, OUT_DIR, PHOTO_DIR, QUERIES, score

MODEL = "owlv2-large"
GRID = (2, 2)        # sütun, satır
OVERLAP = 0.25       # komşu dilimler arası örtüşme oranı
TILE_FILE = OUT_DIR / f"dilimler_{MODEL}.json"


def tiles(width: int, height: int, grid=GRID, overlap=OVERLAP) -> list[tuple[int, int, int, int]]:
    cols, rows = grid
    tw = round(width / (cols - (cols - 1) * overlap))
    th = round(height / (rows - (rows - 1) * overlap))
    xs = [round(i * (width - tw) / (cols - 1)) if cols > 1 else 0 for i in range(cols)]
    ys = [round(j * (height - th) / (rows - 1)) if rows > 1 else 0 for j in range(rows)]
    return [(x, y, x + tw, y + th) for y in ys for x in xs]


def run() -> None:
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import dataclasses
    import warnings
    warnings.filterwarnings("ignore")
    from PIL import Image
    from backend.app import config
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService
    from evaluation.lvis.evaluate_subset import CANDIDATES, candidate_detector

    detector = candidate_detector(MODEL)
    key, floor = CANDIDATES[MODEL]
    # evaluate_masa.run ile aynı politika: tek taban eşiği, sınır yok.
    policy = dataclasses.replace(config.ADAPTIVE_THRESHOLDS[key], thresholds=(floor,), allow_lowering=False,
                                 max_raw_detections=100_000, max_filtered_detections=100_000, max_duplicate_fraction=1.0)
    english = ", ".join(QUERIES)
    plan = process_query(english, TranslationService.__new__(TranslationService), english)
    by_primary = {part["primary_query"]: q for part, q in zip(plan["processed_query_items"], QUERIES)}
    records = []
    for name in LABELS["gorseller"]:
        with Image.open(PHOTO_DIR / name) as source:
            image = source.convert("RGB")
        for index, (x0, y0, x1, y1) in enumerate(tiles(*image.size)):
            t = time.perf_counter()
            result = run_detection(detector, image.crop((x0, y0, x1, y1)), plan, policy)
            records.append({"image": name, "tile": index, "rect": [x0, y0, x1, y1],
                            "seconds": round(time.perf_counter() - t, 1), "detections": [
                {"category": by_primary.get(d["canonical_query"], d["canonical_query"]), "confidence": round(d["confidence"], 4),
                 "box": [round(d["box"]["xmin"] + x0, 1), round(d["box"]["ymin"] + y0, 1),
                         round(d["box"]["xmax"] + x0, 1), round(d["box"]["ymax"] + y0, 1)]}
                for d in result["detections"]]})
            print(f"{name} dilim {index} {len(records[-1]['detections'])} kutu {records[-1]['seconds']}s", flush=True)
            TILE_FILE.write_text(json.dumps({"model": MODEL, "floor": floor, "grid": GRID, "overlap": OVERLAP,
                                             "records": records}, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- birleştirme
def _nms(dets: list[dict], thr: float = 0.5) -> list[dict]:
    kept: list[dict] = []
    for d in sorted(dets, key=lambda d: -d["confidence"]):
        if all(k["category"] != d["category"] or iou(k["box"], d["box"]) < thr for k in kept):
            kept.append(d)
    return kept


def _touches_cut(box, rect, size, margin=8) -> bool:
    """Dilimin görsel kenarı olmayan (kesilmiş) bir kenarına değiyor mu? Böyle kutular
    nesnenin yalnızca bir parçasıdır."""
    w, h = size
    x0, y0, x1, y1 = rect
    return ((x0 > 0 and box[0] <= x0 + margin) or (y0 > 0 and box[1] <= y0 + margin)
            or (x1 < w and box[2] >= x1 - margin) or (y1 < h and box[3] >= y1 - margin))


def variants() -> dict[str, dict]:
    full = {r["image"]: r["detections"] for r in
            json.loads((OUT_DIR / f"tespitler_{MODEL}.json").read_text(encoding="utf-8"))["records"]}
    tile_data = json.loads(TILE_FILE.read_text(encoding="utf-8"))
    sizes = {}
    from PIL import Image
    for name in full:
        with Image.open(PHOTO_DIR / name) as im:
            sizes[name] = im.size
    by_image: dict[str, list[tuple[list, dict]]] = {}
    for r in tile_data["records"]:
        by_image.setdefault(r["image"], []).extend((r["rect"], d) for d in r["detections"])

    def build(keep_tile) -> list[dict]:
        out = []
        for name, dets in full.items():
            extra = [d for rect, d in by_image.get(name, []) if keep_tile(d, rect, sizes[name])]
            out.append({"image": name, "detections": _nms([*dets, *extra])})
        return out

    return {
        "Tam görsel (mevcut)": [{"image": n, "detections": d} for n, d in full.items()],
        "Tam + dilimler (NMS)": build(lambda d, rect, size: True),
        "Tam + dilimler, kesik kutular atılır": build(lambda d, rect, size: not _touches_cut(d["box"], rect, size)),
        # Dilim puanları şişiyor (pil 0.19 → ~0.31); dilim kutusu ayrı eşikle ve yalnızca küçük
        # kutular (görselin <= %1'i) alınır. 0.30 bu 5 fotoğrafta seçildi: aynı veride ayarlandı.
        "Tam + küçük dilim kutuları (dilim eşiği 0.30)": build(
            lambda d, rect, size: d["confidence"] >= 0.30 and not _touches_cut(d["box"], rect, size)
            and (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) <= 0.01 * size[0] * size[1]),
        "Yalnızca dilimler, kesikler atılır": [
            {"image": n, "detections": _nms([d for rect, d in by_image.get(n, []) if not _touches_cut(d["box"], rect, sizes[n])])}
            for n in full],
    }


def report() -> None:
    lines = ["# Dilimleme denemesi: masa fotoğrafları, OWLv2 large", "",
             f"Dilimler: {GRID[0]}×{GRID[1]}, %{OVERLAP * 100:.0f} örtüşme. Tam görsel + 4 dilim = görsel başına 5 forward.",
             "Her satır kendi en iyi eşiğinde ve uygulamanın Sıkı (0.17) / Dengeli (0.14) eşiğinde. IoU >= 0.5.", "",
             "| Yöntem | Eşik | Bulunan nesne | Precision | Recall | F1 | Olmayan nesneye kutu | Bulunamayanlar |",
             "|---|---|---|---|---|---|---|---|"]
    for label, records in variants().items():
        data = {"records": records}
        floor = min((d["confidence"] for r in records for d in r["detections"]), default=0.0)
        grid = [round(floor + 0.01 * k, 2) for k in range(100) if floor + 0.01 * k <= 0.95]
        best_th, _ = max(((th, score(MODEL, th, data)) for th in grid), key=lambda x: x[1]["f1"])
        for th, tag in ((best_th, "en iyi"), (0.17, "Sıkı"), (0.14, "Dengeli")):
            s = score(MODEL, th, data)
            missed = ", ".join(sorted({m.split(" (")[0] for m in s["kacan"]}))
            lines.append(f"| {label} | {th:.2f} ({tag}) | {s['bulunan']}/{s['var']} | {s['p']:.2f} | {s['r']:.2f} | "
                         f"**{s['f1']:.2f}** | {s['uydurma']}/{s['yok']} (%{s['uydurma'] / s['yok'] * 100:.0f}) | {missed or '—'} |")
    text = "\n".join(lines) + "\n\nKüçük örneklem: 5 fotoğraf, 45 nesne.\n"
    (OUT_DIR / "dilimleme.md").write_text(text, encoding="utf-8")
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
