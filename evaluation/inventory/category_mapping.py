"""RPC SKU isimlerini semantic product family'ye dönüştürür."""

import csv
from io import StringIO
import math
import re


def semantic_category(name: str) -> str:
    """97_milk -> milk; ID, numeric prefix'ten tahmin edilmez."""
    match = re.fullmatch(r"\d+_([a-z]+(?:_[a-z]+)*)", name.strip().lower())
    if not match:
        raise ValueError(f"Geçersiz RPC kategori adı: {name!r}")
    return match.group(1).replace("_", " ")


def parse_category_table(text: str) -> dict[int, str]:
    rows = csv.DictReader(StringIO(text))
    if not rows.fieldnames or not {"id", "name"} <= set(rows.fieldnames):
        raise ValueError("categories.csv içinde id/name kolonları bulunamadı.")
    names = {}
    for row in rows:
        category_id = int(row["id"])
        if category_id in names:
            raise ValueError("categories.csv tekrarlı ID içeriyor.")
        semantic_category(row["name"])
        names[category_id] = row["name"].strip()
    if not names:
        raise ValueError("categories.csv boş.")
    return names


def xywh_to_xyxy(bbox) -> list[float]:
    if len(bbox) != 4:
        raise ValueError("bbox tam dört absolute pixel değeri içermelidir.")
    x, y, width, height = map(float, bbox)
    if not all(math.isfinite(value) for value in (x, y, width, height)) or width <= 0 or height <= 0:
        raise ValueError("bbox sonlu değerler ve pozitif genişlik/yükseklik içermelidir.")
    return [x, y, x + width, y + height]
