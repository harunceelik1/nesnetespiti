import re

from PIL import Image, ImageDraw, ImageFont


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
    font = ImageFont.load_default(size=16)

    for detection in detections:
        box = detection["box"]
        xmin, ymin = box["xmin"], box["ymin"]
        xmax, ymax = box["xmax"], box["ymax"]
        draw.rectangle((xmin, ymin, xmax, ymax), outline="red", width=3)

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
