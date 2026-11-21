"""Calibration ground-truth kutularını yerel görüntü kopyaları üzerinde gösterir."""

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

if __package__:
    from .category_mapping import semantic_category
    from .config import CATEGORIES
else:
    from category_mapping import semantic_category
    from config import CATEGORIES


ROOT = Path(__file__).resolve().parent
DEFAULT_CALIBRATION = ROOT / "data" / "calibration"
DEFAULT_OUTPUT = ROOT / "preview"
Warn = Callable[[str], None]
COLORS = ("#c0392b", "#176b43", "#245db5", "#8e44ad", "#916000", "#006d77")
IGNORED_COLOR = "#777777"


@dataclass
class PreviewReport:
    files: list[Path]
    warnings: list[str]


def load_annotations(path: Path, warn: Warn) -> list[dict]:
    """Mevcut annotations.json kayıt listesini oku; hatalı satırları uyararak atla."""
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError("annotations.json bir görüntü kayıt listesi olmalıdır.")
    records = []
    seen = set()
    for index, record in enumerate(content):
        if not isinstance(record, dict):
            warn(f"Kayıt {index}: nesne biçiminde değil, atlandı.")
            continue
        name = record.get("file_name")
        valid_size = all(type(record.get(key)) is int and record[key] > 0 for key in ("width", "height"))
        if (not isinstance(name, str) or not name or name in (".", "..")
                or any(char in name for char in ("/", "\\", ":", "\x00"))
                or not valid_size or not isinstance(record.get("objects"), list)):
            warn(f"Kayıt {index}: dosya adı, boyut veya objects alanı geçersiz; atlandı.")
            continue
        if name in seen:
            warn(f"{name}: tekrarlı görüntü kaydı, atlandı.")
            continue
        seen.add(name)
        records.append(record)
    return records


def drawing_box(bbox, width: int, height: int, warn: Warn, context: str) -> tuple[float, float, float, float] | None:
    """XYXY'yi doğrula; sınır dışı kutuyu yalnızca preview çizimi için kırp."""
    if (not isinstance(bbox, (list, tuple)) or len(bbox) != 4
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in bbox)):
        warn(f"{context}: bbox_xyxy dört sonlu sayı içermeli; kutu atlandı.")
        return None
    xmin, ymin, xmax, ymax = bbox
    if xmax <= xmin or ymax <= ymin:
        warn(f"{context}: sıfır/negatif alanlı kutu atlandı.")
        return None
    if xmin < 0 or ymin < 0 or xmax > width or ymax > height:
        warn(f"{context}: kutu görüntü sınırları dışında; yalnızca preview için kırpılıyor.")
    xmin, ymin = max(0, xmin), max(0, ymin)
    xmax, ymax = min(width, xmax), min(height, ymax)
    if xmax <= xmin or ymax <= ymin:
        warn(f"{context}: görüntüyle kesişmeyen kutu atlandı.")
        return None
    return xmin, ymin, xmax, ymax


def load_full_annotations(path: Path, records: list[dict]) -> dict[str, dict]:
    """Yerel tam annotation kaynağını subset kimlikleriyle eşleştir; ağ kullanma."""
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict) or content.get("complete") is not True or not isinstance(content.get("images"), list):
        raise ValueError("full_annotations.json tamamlanmış bir recovery dosyası değil.")
    lookup = {}
    for item in content["images"]:
        if (not isinstance(item, dict) or not isinstance(item.get("objects"), list)
                or not isinstance(item.get("image_id"), str) or item["image_id"] in lookup):
            raise ValueError("Tam annotation dosyasında geçersiz/tekrarlı kayıt var.")
        lookup[item["image_id"]] = item
    if content.get("image_count") != len(lookup):
        raise ValueError("Tam annotation dosyasının image_count değeri uyuşmuyor.")
    for record in records:
        full = lookup.get(record.get("image_id"))
        if full is None or any(full.get(key) != record.get(key) for key in ("file_name", "width", "height", "source_shard", "source_row_index")):
            raise ValueError(f"{record['file_name']}: tam annotation mevcut subset ile eşleşmiyor.")
    return lookup


def object_family(item) -> str | None:
    if not isinstance(item, dict):
        return None
    name = item.get("original_category_name")
    if isinstance(name, str):
        try:
            return semantic_category(name)
        except ValueError:
            pass
    family = item.get("evaluation_category")
    return family.strip() if isinstance(family, str) and family.strip() else None


def draw_ground_truth(image: Image.Image, record: dict, warn: Warn, *, mode: str = "selected", full_record: dict | None = None) -> Image.Image:
    """Girdi PIL görüntüsünü değiştirmeden bütün geçerli GT kutularını çiz."""
    if mode not in ("selected", "all"):
        raise ValueError("mode selected veya all olmalıdır.")
    if mode == "all" and full_record is None:
        raise ValueError("all modu tam RPC annotation gerektirir; selected kayıtlar yeterli değildir.")
    annotated = image.convert("RGB")
    width, height = annotated.size
    if (record["width"], record["height"]) != (width, height):
        warn(f"{record['file_name']}: annotation boyutu {record['width']}x{record['height']}, gerçek boyut {width}x{height}; çizimde gerçek boyut kullanılıyor.")
    draw = ImageDraw.Draw(annotated)
    font_size = max(12, round(min(width, height) / 70))
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default(size=font_size)
    line_width = max(2, round(min(width, height) / 500))
    objects = full_record["objects"] if mode == "all" else record["objects"]
    for index, item in enumerate(objects):
        context = f"{record['file_name']} / nesne {index}"
        family = object_family(item)
        if family is None:
            warn(f"{context}: evaluation_category geçersiz; kutu atlandı.")
            continue
        selected = family in CATEGORIES
        if mode == "selected" and not selected:
            continue
        box = drawing_box(item.get("bbox_xyxy"), width, height, warn, context)
        if box is None:
            continue
        label = family
        if not selected and isinstance(item.get("original_category_name"), str):
            label += f" ({item['original_category_name']})"
        color = COLORS[hashlib.sha256(family.encode("utf-8")).digest()[0] % len(COLORS)] if selected else IGNORED_COLOR
        xmin, ymin, xmax, ymax = box
        draw.rectangle((min(xmin, width - 1), min(ymin, height - 1), min(xmax, width - 1), min(ymax, height - 1)), outline=color, width=line_width)
        # Etiket arka planı görüntü içinde kalır; kutu üstünde yer yoksa içeri alınır.
        text_box = draw.textbbox((0, 0), label, font=font)
        label_width, label_height = text_box[2] - text_box[0] + 8, text_box[3] - text_box[1] + 6
        left = max(0, min(xmin, width - label_width))
        top = max(0, min(ymin - label_height, height - label_height))
        draw.rectangle((left, top, min(width - 1, left + label_width), min(height - 1, top + label_height)), fill=color)
        draw.text((left + 4 - text_box[0], top + 3 - text_box[1]), label, fill="white", font=font)
    # Filtrelenmiş subset'ten RPC toplamı uydurulmaz. Tam kaynak yoksa ? göster.
    count_selected = sum(object_family(item) in CATEGORIES for item in record["objects"])
    if full_record is not None:
        total = len(full_record["objects"])
        count_selected = sum(object_family(item) in CATEGORIES for item in full_record["objects"])
        summary = f"RPC objects: {total} | Selected objects: {count_selected} | Ignored objects: {total - count_selected}"
    else:
        summary = f"RPC objects: ? | Selected objects: {count_selected} | Ignored objects: ?"
    summary_box = draw.textbbox((0, 0), summary, font=font)
    draw.rectangle((0, 0, min(width - 1, summary_box[2] + 12), min(height - 1, summary_box[3] - summary_box[1] + 12)), fill="#242424")
    draw.text((6, 6 - summary_box[1]), summary, fill="white", font=font)
    return annotated


def generate_previews(count: int = 15, seed: int = 42, *, calibration: Path = DEFAULT_CALIBRATION, output: Path = DEFAULT_OUTPUT, mode: str = "selected") -> PreviewReport:
    if count < 1:
        raise ValueError("count pozitif olmalıdır.")
    if mode not in ("selected", "all"):
        raise ValueError("mode selected veya all olmalıdır.")
    # Dataset klasörünü yanlışlıkla çıktı olarak kullanma; symlink'ler de çözülür.
    if output.resolve().is_relative_to(calibration.parent.resolve()):
        raise ValueError("Preview çıktısı dataset data/ klasörünün dışında olmalıdır.")
    messages = []
    def warn(message: str):
        messages.append(message)
        print("WARNING: " + message, file=sys.stderr)
    records = load_annotations(calibration / "annotations.json", warn)
    full_path = calibration.parent / "full_annotations.json"
    if mode == "all" and not full_path.is_file():
        raise ValueError("all modu için data/full_annotations.json gerekli. Önce recover_full_annotations.py --dry-run ile planı inceleyin; recovery ayrı ve ağ erişimi olan bir adımdır.")
    full_records = load_full_annotations(full_path, records) if full_path.is_file() else {}
    if count > len(records):
        warn(f"İstenen {count} görüntüye karşılık {len(records)} geçerli calibration kaydı var; mevcut kayıtlar kullanılacak.")
    selected = random.Random(seed).sample(records, min(count, len(records)))
    files = []
    if selected:
        output.mkdir(parents=True, exist_ok=True)
    images_dir = (calibration / "images").resolve()
    for record in selected:
        source_path = (images_dir / record["file_name"]).resolve()
        if source_path.parent != images_dir:
            warn(f"{record['file_name']}: kaynak images/ klasörü dışında, atlandı.")
            continue
        suffix = "_ground_truth_all.jpg" if mode == "all" else "_ground_truth.jpg"
        destination = output / (Path(record["file_name"]).stem + suffix)
        if destination.is_symlink():
            warn(f"{destination.name}: çıktı symlink olduğundan atlandı.")
            continue
        try:
            with Image.open(source_path) as image:
                with draw_ground_truth(image, record, warn, mode=mode, full_record=full_records.get(record.get("image_id"))) as annotated:
                    annotated.save(destination, format="JPEG", quality=95)
            files.append(destination)
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError, ValueError) as exc:
            warn(f"{record['file_name']}: preview oluşturulamadı ({exc}); diğer görüntülere devam ediliyor.")
    return PreviewReport(files=files, warnings=messages)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mode", choices=("selected", "all"), default="selected")
    args = parser.parse_args(argv)
    try:
        report = generate_previews(args.count, args.seed, mode=args.mode)
    except (OSError, ValueError) as exc:
        print(f"Preview hazırlanamadı: {exc}", file=sys.stderr)
        return 1
    print(f"{len(report.files)} preview üretildi; {len(report.warnings)} warning. Çıktı: {DEFAULT_OUTPUT}")
    return 0 if report.files else 1


if __name__ == "__main__":
    raise SystemExit(main())
