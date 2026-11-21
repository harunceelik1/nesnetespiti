from pathlib import Path

import torch
from PIL import Image, ImageDraw
from transformers import OwlViTForObjectDetection, OwlViTProcessor


BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "images" / "test.jpg"
OUTPUT_PATH = BASE_DIR / "outputs" / "result.jpg"

MODEL_NAME = "google/owlvit-base-patch32"
OBJECTS = ["person", "car", "dog"]
CONFIDENCE_THRESHOLD = 0.1


def main():
    if not IMAGE_PATH.is_file():
        raise FileNotFoundError(f"Test görüntüsünü bu konuma koyun: {IMAGE_PATH}")

    # RGB dönüşümü, görüntünün modelin beklediği üç renk kanalını taşımasını sağlar.
    with Image.open(IMAGE_PATH) as source:
        image = source.convert("RGB")

    # İlk çalıştırmada pretrained model ve işlemci Hugging Face'den indirilir.
    # Başlangıç için CPU kullanıyoruz; CUDA kurulumu gerekli değildir.
    processor = OwlViTProcessor.from_pretrained(MODEL_NAME)
    model = OwlViTForObjectDetection.from_pretrained(MODEL_NAME)
    model.eval()

    # Tek görüntü için aranacak nesneler bir iç liste olarak verilir.
    text_labels = [OBJECTS]
    inputs = processor(text=text_labels, images=image, return_tensors="pt")
    with torch.inference_mode():
        predictions = model(**inputs)

    # Kutuları orijinal görüntünün piksel boyutlarına ölçekle.
    results = processor.post_process_grounded_object_detection(
        outputs=predictions,
        target_sizes=torch.tensor([[image.height, image.width]]),
        threshold=CONFIDENCE_THRESHOLD,
        text_labels=text_labels,
    )[0]

    draw = ImageDraw.Draw(image)
    for box, label, score in zip(
        results["boxes"], results["text_labels"], results["scores"]
    ):
        x1, y1, x2, y2 = box.tolist()
        caption = f"{label}: {score.item():.2f}"
        draw.rectangle((x1, y1, x2, y2), outline="red", width=3)

        # Yazıyı görüntü sınırları içinde tut ve okunması için arka plan çiz.
        text_width = draw.textbbox((0, 0), caption)[2]
        text_x = max(0, min(x1, image.width - text_width))
        text_y = max(0, min(y1 - 14, image.height - 14))
        draw.rectangle(draw.textbbox((text_x, text_y), caption), fill="red")
        draw.text((text_x, text_y), caption, fill="white")
        print(f"{caption} | box: {[round(value, 2) for value in box.tolist()]}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PATH)
    print(f"Tespit sayısı: {len(results['boxes'])}")
    print(f"Sonuç kaydedildi: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
