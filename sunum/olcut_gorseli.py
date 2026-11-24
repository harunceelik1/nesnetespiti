"""Sunumdaki ölçüt slaytları için açıklama görselleri (LVIS ana kümesinden, OWLv2 large kayıtlarıyla).

Model yeniden çalıştırılmaz: kayıtlı tespitler (outputs/lvis_olcum/tespitler_ana_owlv2-large.json)
uygulamanın Dengeli eşiğiyle süzülür ve ölçümdeki eşleşmenin aynısı (IoU >= 0.5, açgözlü) çizilir.

Üretilenler (sunum/aciklama/):
  olcut_ornegi.jpg  bir görselde doğru kutu / yanlış kutu / kaçırılan nesne + o görselin precision, recall, F1'i
  iou_ornegi.jpg    IoU'nun ne olduğu: gerçek kutu ile tahmin kutusunun örtüşmesi (biri geçer, biri geçmez)

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe sunum\\olcut_gorseli.py              # seçili görselle üret
  .venv\\Scripts\\python.exe sunum\\olcut_gorseli.py --aday       # aday görsellerin önizlemesi
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import config  # noqa: E402
from evaluation.lvis.evaluate_subset import IMAGE_DIR, IOU_MATCH, detections_path, iou, query_names, subset_path  # noqa: E402

OUT = Path(__file__).resolve().parent / "aciklama"
THRESHOLD = config.ADAPTIVE_THRESHOLDS["owlv2-large"].thresholds[0]  # Dengeli
SECILEN = 63848  # olcut_ornegi.jpg için seçilen LVIS görseli: nadir "omlet" doğru, uydurma ("cider"), kaçırılan masa
GREEN, RED, YELLOW = (46, 170, 110), (220, 60, 60), (245, 197, 24)
INK, PAPER, MUTED, SIGNAL = (15, 27, 45), (236, 240, 244), (96, 110, 128), (0, 150, 170)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", size)
    except OSError:
        return ImageFont.truetype("arial.ttf", size)


def analyse(record: dict, item: dict) -> dict:
    """Ölçümdeki eşleşmenin aynısı: her kategori için puan sırasıyla açgözlü bire bir, IoU >= 0.5."""
    kept = [d for d in record["detections"] if d["confidence"] >= THRESHOLD]
    tp, fp, fn, uydurma = [], [], [], []
    for category in record["positives"]:
        gt = [[x, y, x + w, y + h] for x, y, w, h in item["positives"][category]]
        used = {}
        for d in sorted((d for d in kept if d["category"] == category), key=lambda d: -d["confidence"]):
            best, best_i = IOU_MATCH, None
            for i, g in enumerate(gt):
                if i not in used and iou(d["box"], g) >= best:
                    best, best_i = iou(d["box"], g), i
            if best_i is None:
                near = max((iou(d["box"], g) for g in gt), default=0.0)
                fp.append({**d, "iou": near})
            else:
                used[best_i] = d
                tp.append({**d, "iou": best, "gt": gt[best_i]})
        fn += [{"category": category, "box": g} for i, g in enumerate(gt) if i not in used]
    for category in record["negatives"]:
        uydurma += [d for d in kept if d["category"] == category]
    return {"tp": tp, "fp": fp, "fn": fn, "uydurma": uydurma,
            "positives": record["positives"], "negatives": record["negatives"]}


def dashed(draw: ImageDraw.ImageDraw, box, color, width: int, dash: int = 14) -> None:
    x0, y0, x1, y1 = box
    for a, b, horizontal, fixed in ((x0, x1, True, y0), (x0, x1, True, y1), (y0, y1, False, x0), (y0, y1, False, x1)):
        pos = a
        while pos < b:
            end = min(pos + dash, b)
            draw.line([(pos, fixed), (end, fixed)] if horizontal else [(fixed, pos), (fixed, end)], fill=color, width=width)
            pos += dash * 2


def label(draw, xy, text, color, size):
    f = font(size)
    x, y = xy
    w = draw.textlength(text, font=f)
    y = max(0, y - size - 6)
    draw.rectangle([x, y, x + w + 10, y + size + 6], fill=color)
    draw.text((x + 5, y + 2), text, fill=(255, 255, 255) if color != YELLOW else INK, font=f)


def annotate(image: Image.Image, result: dict, names: dict, scale: float) -> Image.Image:
    image = image.resize((round(image.width * scale), round(image.height * scale)))
    draw = ImageDraw.Draw(image)
    s = lambda b: [v * scale for v in b]
    lw, size = max(3, round(image.width / 220)), max(16, round(image.width / 48))
    for d in result["fn"]:
        box = s(d["box"])
        dashed(draw, box, YELLOW, lw)
        # Kaçırılan etiketi kutunun alt kenarına: üst kenardaki tespit etiketleriyle çakışmasın.
        label(draw, (box[0] + lw, box[3] - lw), f"kaçırılan: {names[d['category']]}", YELLOW, size)
    for d in result["fp"]:
        draw.rectangle(s(d["box"]), outline=RED, width=lw)
        label(draw, s(d["box"])[:2], f"yanlış: {names[d['category']]} {d['confidence']:.2f}", RED, size)
    for d in result["uydurma"]:
        draw.rectangle(s(d["box"]), outline=RED, width=lw)
        label(draw, s(d["box"])[:2], f"uydurma ('yok' sorusu): {names[d['category']]} {d['confidence']:.2f}", RED, size)
    for d in result["tp"]:
        draw.rectangle(s(d["box"]), outline=GREEN, width=lw)
        label(draw, s(d["box"])[:2], f"doğru: {names[d['category']]} {d['confidence']:.2f}", GREEN, size)
    return image


def panel(result: dict, names: dict, height: int) -> Image.Image:
    width = 560
    img = Image.new("RGB", (width, height), PAPER)
    d = ImageDraw.Draw(img)
    tp, fp, fn = len(result["tp"]), len(result["fp"]) + len(result["uydurma"]), len(result["fn"])
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    y = 28
    d.text((28, y), "Bu görselde sorulanlar", fill=INK, font=font(30)); y += 50
    for c in result["positives"]:
        d.text((28, y), f"var  · {names[c]}", fill=INK, font=font(24)); y += 34
    for c in result["negatives"]:
        d.text((28, y), f"yok · {names[c]}", fill=MUTED, font=font(24)); y += 34
    y += 18
    rows = [(GREEN, f"{tp} doğru kutu", "gerçek nesneyle örtüşmesi (IoU) en az 0.5"),
            (RED, f"{fp} yanlış kutu", "eşleşmedi ya da olmayan nesne"),
            (YELLOW, f"{fn} kaçırılan nesne", "hiç kutu çizilmedi")]
    for color, big, small in rows:
        d.rectangle([28, y + 6, 52, y + 30], fill=color)
        d.text((66, y), big, fill=INK, font=font(28)); d.text((66, y + 36), small, fill=MUTED, font=font(20)); y += 76
    y += 8
    d.line([(28, y), (width - 28, y)], fill=MUTED, width=2); y += 22
    for name, formula, value in (("Precision", f"{tp} / ({tp} + {fp})", p), ("Recall", f"{tp} / ({tp} + {fn})", r),
                                 ("F1", "iki oranın harmonik ortalaması", f1)):
        d.text((28, y), name, fill=INK, font=font(28))
        d.text((width - 28 - d.textlength(f"{value:.2f}", font=font(34)), y - 4), f"{value:.2f}", fill=SIGNAL, font=font(34))
        d.text((28, y + 36), formula, fill=MUTED, font=font(20)); y += 74
    return img


def olcut_ornegi(record, item, names) -> Image.Image:
    result = analyse(record, item)
    with Image.open(IMAGE_DIR / item["file_name"]) as source:
        image = source.convert("RGB")
    scale = 900 / image.height
    left = annotate(image, result, names, scale)
    right = panel(result, names, left.height)
    sheet = Image.new("RGB", (left.width + right.width, left.height), PAPER)
    sheet.paste(left, (0, 0)); sheet.paste(right, (left.width, 0))
    return sheet


def iou_ornegi(record, item, names) -> Image.Image:
    """Aynı görselden bir doğru kutu (IoU en az 0.5) ve bir yanlış kutu (IoU < 0.5): yakın plan."""
    result = analyse(record, item)
    with Image.open(IMAGE_DIR / item["file_name"]) as source:
        image = source.convert("RGB")
    cases = []
    if result["tp"]:
        cases.append((max(result["tp"], key=lambda d: d["iou"]), True))
    near_fp = [d for d in result["fp"] if d["iou"] > 0]
    if near_fp:
        d = max(near_fp, key=lambda d: d["iou"])
        gt = [[x, y, x + w, y + h] for x, y, w, h in item["positives"][d["category"]]]
        cases.append(({**d, "gt": max(gt, key=lambda g: iou(d["box"], g))}, False))
    tiles = []
    for d, ok in cases:
        g, b = d["gt"], d["box"]
        x0, y0 = min(g[0], b[0]), min(g[1], b[1])
        x1, y1 = max(g[2], b[2]), max(g[3], b[3])
        pad = 0.25 * max(x1 - x0, y1 - y0)
        crop = [max(0, x0 - pad), max(0, y0 - pad), min(image.width, x1 + pad), min(image.height, y1 + pad)]
        tile = image.crop(crop)
        scale = 520 / max(tile.size)
        tile = tile.resize((round(tile.width * scale), round(tile.height * scale)))
        draw = ImageDraw.Draw(tile)
        m = lambda bx: [(bx[0] - crop[0]) * scale, (bx[1] - crop[1]) * scale, (bx[2] - crop[0]) * scale, (bx[3] - crop[1]) * scale]
        dashed(draw, m(g), YELLOW, 4)
        draw.rectangle(m(b), outline=GREEN if ok else RED, width=4)
        canvas = Image.new("RGB", (560, tile.height + 150), PAPER)
        canvas.paste(tile, ((560 - tile.width) // 2, 20))
        cd = ImageDraw.Draw(canvas)
        verdict = "0.5 ve üstü: doğru kutu" if ok else "0.5'ten küçük: yanlış kutu"
        cd.text((20, tile.height + 36), f"{names[d['category']]}:  IoU = {d['iou']:.2f}", fill=INK, font=font(30))
        cd.text((20, tile.height + 80), verdict, fill=GREEN if ok else RED, font=font(28))
        tiles.append(canvas)
    head = 120
    sheet = Image.new("RGB", (560 * len(tiles), max(t.height for t in tiles) + head), PAPER)
    sd = ImageDraw.Draw(sheet)
    sd.text((20, 20), "IoU = örtüşen alan / iki kutunun birleşimi", fill=INK, font=font(32))
    sd.text((20, 66), "sarı kesikli: gerçek nesne (etiket) · renkli: modelin kutusu", fill=MUTED, font=font(22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (560 * i, head))
    return sheet


def main() -> None:
    subset = {i["image_id"]: i for i in json.loads(subset_path("ana").read_text(encoding="utf-8"))}
    records = {r["image_id"]: r for r in json.loads(detections_path("ana", "owlv2-large").read_text(encoding="utf-8"))["records"]}
    names = query_names(list(subset.values()))
    OUT.mkdir(exist_ok=True)
    if "--aday" in sys.argv:
        for image_id in (116031, 170877, 255824, 567836, 63848, 321071, 183675, 128002):
            sheet = olcut_ornegi(records[image_id], subset[image_id], names)
            sheet.thumbnail((1000, 1000))
            sheet.save(OUT / f"aday_{image_id}.jpg", quality=85)
        print(f"Adaylar: {OUT}")
        return
    olcut_ornegi(records[SECILEN], subset[SECILEN], names).save(OUT / "olcut_ornegi.jpg", quality=92)
    iou_ornegi(records[SECILEN], subset[SECILEN], names).save(OUT / "iou_ornegi.jpg", quality=92)
    print(f"Kaydedildi: {OUT}")


if __name__ == "__main__":
    main()
