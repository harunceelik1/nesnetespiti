"""LVIS v1 val'den ödev senaryolarına göre 50 görsellik ölçüm alt kümesi seçer.

Seçim fotoğraflara bakılarak değil, LVIS etiketleriyle yapılır:
  masa      : robotik / masa üstü nesneleri (kupa, kalem, kumanda, makas, telefon…)
  envanter  : aynı nesneden en az 3 tane (şişe, kutu, kavanoz…)
  guvenlik  : çanta, bıçak, kask, silah, kilit…
  kucuk     : kutusu görselin %1'inden küçük nesne (pil, anahtar, yüzük…)
  benzer    : birbirine benzeyen nesnelerin bir arada olduğu sahneler (şişe/sprey/kavanoz, kupa/bardak…)
Her görselde en az 3 "kesinlikle yok" (neg) kategori bulunur; yanlış kutu ölçümü bunlarla yapılır.
Seçim sabit tohumla yapılır (aynı komut her seferinde aynı 50 görseli seçer).

Çalıştırma (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.select_subset            # seç + subset_50.json yaz
  .venv\\Scripts\\python.exe -m evaluation.lvis.select_subset --download # + görselleri indir, önizleme üret
Etiket dosyası: .cache/lvis/lvis_v1_val.json (https://dl.fbaipublicfiles.com/LVIS/lvis_v1_val.json.zip)
"""

from __future__ import annotations

import argparse
import json
import random
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = ROOT / ".cache" / "lvis" / "lvis_v1_val.json"
IMAGE_DIR = ROOT / ".cache" / "lvis" / "images"
SUBSET_FILE = Path(__file__).with_name("subset_50.json")
PREVIEW = ROOT / "outputs" / "lvis_alt_kume" / "onizleme.jpg"
SEED = 42

# Masa / tezgâh / raf bağlamı: masa üstü ve küçük nesne gruplarında en az biri etiketli olmalı.
SURFACES = {"table", "desk", "dining_table", "kitchen_table", "coffee_table", "tray", "bookcase",
            "cabinet", "cupboard", "file_cabinet", "spice_rack", "tablecloth"}

GROUPS: dict[str, dict] = {
    # Robotik / masa üstü: en az 2 farklı masa nesnesi + bir yüzey.
    "masa": {"count": 12, "min_categories": 2, "surface": True, "cats": {
        "cup", "mug", "pen", "pencil", "remote_control", "scissors", "cellular_telephone",
        "mouse_(computer_equipment)", "computer_keyboard", "laptop_computer", "book", "stapler_(stapling_machine)",
        "glass_(drink_container)", "headset", "earphone", "spectacles", "sunglasses", "notebook", "marker",
        "wallet", "bottle", "water_bottle", "jar", "box", "tape_(sticky_cloth_or_paper)", "calculator"}},
    # Envanter: kap / ürün (yiyecek değil); bir kategoriden en az 3 tane, en az 2 farklı ürün kategorisi.
    "envanter": {"count": 12, "min_instances": 3, "min_categories": 2, "cats": {
        "bottle", "water_bottle", "wine_bottle", "beer_bottle", "can", "beer_can", "jar", "box", "carton",
        "aerosol_can", "pop_(soda)", "mug", "cup", "book", "glass_(drink_container)", "bowl", "canister",
        "basket", "bag", "plastic_bag", "paper_bag", "shopping_bag"}},
    # Güvenlik: bagaj / çanta / kask / silah / kilit (mutfak bıçağı yok).
    "guvenlik": {"count": 10, "cats": {
        "backpack", "handbag", "suitcase", "helmet", "gun", "pistol", "rifle", "pocketknife",
        "padlock", "combination_lock", "bulletproof_vest", "cone", "fire_extinguisher", "duffel_bag"}},
    # Küçük nesne: görselin %1'inden küçük kutulu, masa üstünde duran eşya (takı yok) + bir yüzey.
    "kucuk": {"count": 10, "max_area_ratio": 0.01, "surface": True, "cats": {
        "battery", "key", "screwdriver", "bottle_cap", "remote_control", "cellular_telephone", "padlock",
        "pen", "pencil", "marker", "coin", "penny_(coin)", "scissors", "mouse_(computer_equipment)",
        "spectacles", "wallet", "tape_(sticky_cloth_or_paper)", "earphone", "jar", "cup", "mug"}},
    # Benzer görünen nesneler bir arada (yiyecek/çatal-bıçak eşleri yok).
    "benzer": {"count": 6, "pairs": [
        {"bottle", "aerosol_can"}, {"bottle", "jar"}, {"cup", "mug"}, {"cup", "glass_(drink_container)"},
        {"mug", "glass_(drink_container)"}, {"handbag", "backpack"}, {"wine_bottle", "water_bottle"},
        {"bottle", "wine_bottle"}, {"can", "jar"}, {"remote_control", "cellular_telephone"},
        {"pen", "pencil"}, {"pen", "marker"}, {"bottle", "glass_(drink_container)"}]},
}


def load():
    data = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    names = {c["id"]: c["name"] for c in data["categories"]}
    anns = defaultdict(list)
    for ann in data["annotations"]:
        anns[ann["image_id"]].append(ann)
    return data["images"], anns, names


def matches(group: str, spec: dict, image: dict, anns: list[dict], names: dict) -> bool:
    not_exhaustive = {names[c] for c in image.get("not_exhaustive_category_ids", [])}
    counts = Counter(names[a["category_id"]] for a in anns)
    area = image["width"] * image["height"]
    if group == "benzer":
        present = {n for n in counts if n not in not_exhaustive}
        return any(pair <= present for pair in spec["pairs"])
    if spec.get("surface") and not (set(counts) & SURFACES):
        return False
    # Senaryo kategorileri tam etiketlenmiş olmalı (not_exhaustive değil).
    relevant = {n: c for n, c in counts.items() if n in spec["cats"] and n not in not_exhaustive}
    if len(relevant) < spec.get("min_categories", 1):
        return False
    if "min_instances" in spec:
        return max(relevant.values()) >= spec["min_instances"]
    if "max_area_ratio" in spec:
        return any(names[a["category_id"]] in relevant and a["bbox"][2] * a["bbox"][3] / area < spec["max_area_ratio"]
                   for a in anns)
    return True


def select() -> list[dict]:
    images, anns, names = load()
    candidates = [img for img in images
                  if len(img.get("neg_category_ids", [])) >= 3
                  and len({a["category_id"] for a in anns[img["id"]]}) >= 3]
    rng = random.Random(SEED)
    rng.shuffle(candidates)
    chosen, used = [], set()
    for group, spec in GROUPS.items():
        picked = 0
        for image in candidates:
            if picked == spec["count"]:
                break
            if image["id"] in used or not matches(group, spec, image, anns[image["id"]], names):
                continue
            used.add(image["id"])
            picked += 1
            positives = defaultdict(list)
            for a in anns[image["id"]]:
                positives[names[a["category_id"]]].append([round(v, 1) for v in a["bbox"]])
            chosen.append({
                "image_id": image["id"], "group": group, "coco_url": image["coco_url"],
                "file_name": image["coco_url"].rsplit("/", 1)[-1],
                # Görselin bu gruba girme nedeni olan kategoriler (önizleme ve rapor için).
                "focus": sorted({names[a["category_id"]] for a in anns[image["id"]]}
                                & (spec.get("cats") or set().union(*spec.get("pairs", [set()])))),
                "width": image["width"], "height": image["height"],
                "positives": dict(sorted(positives.items())),
                "negatives": sorted(names[c] for c in image["neg_category_ids"]),
                "not_exhaustive": sorted(names[c] for c in image.get("not_exhaustive_category_ids", [])),
            })
        print(f"{group:9s} {picked}/{spec['count']}")
    return chosen


def download(subset: list[dict]) -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for item in subset:
        target = IMAGE_DIR / item["file_name"]
        if not target.exists():
            urllib.request.urlretrieve(item["coco_url"], target)


def preview(subset: list[dict]) -> None:
    from PIL import Image, ImageDraw
    cell, cols = 320, 5
    rows = (len(subset) + cols - 1) // cols
    sheet = Image.new("RGB", (cell * cols, (cell + 22) * rows), "white")
    draw_sheet = ImageDraw.Draw(sheet)
    palette = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6"]
    for index, item in enumerate(subset):
        with Image.open(IMAGE_DIR / item["file_name"]) as source:
            image = source.convert("RGB")
        scale = cell / max(image.size)
        image = image.resize((round(image.width * scale), round(image.height * scale)))
        draw = ImageDraw.Draw(image)
        for color_index, (name, boxes) in enumerate(item["positives"].items()):
            color = palette[color_index % len(palette)]
            for x, y, w, h in boxes:
                draw.rectangle([x * scale, y * scale, (x + w) * scale, (y + h) * scale], outline=color, width=2)
        x0, y0 = (index % cols) * cell, (index // cols) * (cell + 22)
        sheet.paste(image, (x0 + (cell - image.width) // 2, y0))
        label = f"{index + 1}. {item['group']} · " + ", ".join(item["focus"][:3])
        draw_sheet.text((x0 + 4, y0 + cell + 4), label[:52], fill="black")
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW, quality=85)
    print(f"Önizleme: {PREVIEW}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="görselleri COCO sunucusundan indir ve önizleme üret")
    args = parser.parse_args()
    subset = select()
    SUBSET_FILE.write_text(json.dumps(subset, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(subset)} görsel → {SUBSET_FILE}")
    stats = Counter(n for item in subset for n in item["positives"])
    print("En sık kategoriler:", stats.most_common(15))
    print("Toplam pozitif kategori-görsel çifti:", sum(len(i["positives"]) for i in subset),
          "· negatif:", sum(len(i["negatives"]) for i in subset))
    if args.download:
        download(subset)
        preview(subset)


if __name__ == "__main__":
    main()
