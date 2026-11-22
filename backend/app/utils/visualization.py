import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font_candidates() -> list[str]:
    # Pillow'un yerleşik fontunda ı, ş, ğ, İ yok ("at▯▯t▯rmal▯k" çiziliyordu).
    # Türkçe karakterli bir TrueType font: matplotlib'in DejaVu Sans'ı (venv'de var),
    # yoksa sistemdeki DejaVu Sans / Arial; hiçbiri yoksa yerleşik font.
    candidates = []
    try:
        import matplotlib
        candidates.append(str(Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf" / "DejaVuSans.ttf"))
    except ImportError:
        pass
    return candidates + ["DejaVuSans.ttf", "arial.ttf"]


@lru_cache(maxsize=16)
def label_font(size: int) -> ImageFont.ImageFont:
    for candidate in _font_candidates():
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def format_detection_label(label: str, confidence: float) -> str:
    """Etiketi tek sınıf adı ve güncel confidence değeriyle biçimlendirir."""
    # Label içinde önceden eklenmiş skor varsa yeniden yazılmasını önle.
    label = re.sub(r"(?::\s*(?:\d+(?:\.\d*)?|\.\d+)\s*)+$", "", label).strip()
    parts = [part.strip() for part in label.split(":")]
    if len(parts) > 1 and all(part == parts[0] for part in parts):
        label = parts[0]
    return f"{label}: {confidence:.2f}"


def annotate_image(image: Image.Image, detections: list[dict]) -> Image.Image:
    """Orijinal görüntüyü değiştirmeden kutuları ve etiketleri çizilmiş kopya döndürür."""
    annotated = image.convert("RGB")
    draw = ImageDraw.Draw(annotated)
    # Büyük görseller arayüzde küçültülerek gösterilir; yazı ve çizgi görsel
    # boyutuyla ölçeklenir (1860 px envanter görselinde ~37 px yazı, 4 px çizgi).
    short_side = min(annotated.width, annotated.height)
    font = label_font(max(16, round(short_side / 50)))
    line_width = max(3, round(short_side / 450))

    for detection in detections:
        box = detection["box"]
        xmin, ymin = box["xmin"], box["ymin"]
        xmax, ymax = box["xmax"], box["ymax"]
        draw.rectangle((xmin, ymin, xmax, ymax), outline="red", width=line_width)

        caption = format_detection_label(detection["label"], detection["confidence"])
        left, top, right, bottom = draw.textbbox((0, 0), caption, font=font)
        text_width, text_height = right - left, bottom - top

        # Etiketi kutunun üstüne yerleştir; üst kenarda ise görüntü içinde tut.
        x = max(0, min(xmin, annotated.width - text_width - 8))
        y = max(0, min(ymin - text_height - 8, annotated.height - text_height - 8))
        draw.rectangle(
            (x, y, x + text_width + 8, y + text_height + 8), fill="red"
        )
        draw.text((x + 4 - left, y + 4 - top), caption, fill="white", font=font)

    return annotated
