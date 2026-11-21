"""Hazır evaluation kutularından iki panelli debug görüntüsü; inference içermez."""

from PIL import Image, ImageDraw, ImageFont

from .metrics import xyxy


GT_COLOR = "#16804a"
PREDICTION_COLOR = "#c45b12"


def load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def draw_panel(image: Image.Image, items: list[tuple], color: str):
    """Clipping sadece çizimdedir; kaynak kutu/skorlar ve metric girdileri değişmez."""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    font = load_font(max(12, round(min(width, height) / 75)))
    thickness = max(2, round(min(width, height) / 450))
    for label, box, confidence in items:
        xmin, ymin, xmax, ymax = xyxy(box)
        left, top = max(0, xmin), max(0, ymin)
        right, bottom = min(width - 1, xmax), min(height - 1, ymax)
        if right < left or bottom < top:
            continue  # Tamamen görüntü dışındaki kutu bir piksele çizilemez.
        draw.rectangle((left, top, right, bottom), outline=color, width=thickness)
        text = label if confidence is None else f"{label}: {confidence:.3f}"
        bounds = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bounds[2] - bounds[0] + 8, bounds[3] - bounds[1] + 6
        x = max(0, min(left, width - text_width))
        y = max(0, min(top - text_height, height - text_height))
        draw.rectangle((x, y, min(width - 1, x + text_width), min(height - 1, y + text_height)), fill=color)
        draw.text((x + 4 - bounds[0], y + 3 - bounds[1]), text, font=font, fill="white")


def render_debug_image(image: Image.Image, ground_truth: list[dict], predictions: list[dict], *, model: str, image_id: str) -> Image.Image:
    """Sol GT (yeşil), sağ mevcut NMS sonrası prediction (turuncu + confidence)."""
    width, height = image.size
    font = load_font(max(14, round(min(width, height) / 60)))
    header_height = max(56, round(min(width, height) / 25))
    gap = max(10, round(width / 100))
    with image.convert("RGB") as left, image.convert("RGB") as right:
        draw_panel(left, [(obj["evaluation_category"], obj["bbox_xyxy"], None) for obj in ground_truth], GT_COLOR)
        draw_panel(right, [(obj["label"], obj["box"], obj["confidence"]) for obj in predictions], PREDICTION_COLOR)
        canvas = Image.new("RGB", (2 * width + gap, height + header_height), "#f4f4f4")
        canvas.paste(left, (0, header_height))
        canvas.paste(right, (width + gap, header_height))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 4), f"GROUND TRUTH ({len(ground_truth)})", font=font, fill=GT_COLOR)
    draw.text((width + gap + 8, 4), f"PREDICTIONS - {model} ({len(predictions)})", font=font, fill=PREDICTION_COLOR)
    small_font = load_font(max(10, round(min(width, height) / 95)))
    draw.text((8, header_height // 2), image_id, font=small_font, fill="#444444")
    return canvas
