import torch
from PIL import Image
from transformers import OwlViTForObjectDetection, OwlViTProcessor

from .base_detector import BaseDetector


class OwlViTService(BaseDetector):
    """Bir model örneğini tüm tespit isteklerinde yeniden kullanır."""

    model_id = "owlvit"
    name = "OWL-ViT"
    # Eski JSON model alanı geriye uyumluluk için korunur.
    response_model = "OWL-ViT"
    device = "cpu"
    use_contrastive_queries = True

    def __init__(self):
        model_name = "google/owlvit-base-patch32"
        # İlk kullanımda indirilir; sonraki açılışlarda Hugging Face önbelleği kullanılır.
        # Bu kurucu yalnızca uygulama başlangıcında çağrılır, her istekte çağrılmaz.
        self.processor = OwlViTProcessor.from_pretrained(model_name)
        self.model = OwlViTForObjectDetection.from_pretrained(model_name)
        self.model.eval()
        # Başlangıç için CPU kullanılır; CUDA kurulumu gerekmez.

    def _target_sizes(self, image: Image.Image) -> torch.Tensor:
        return torch.tensor([[image.height, image.width]])

    def _infer_raw(self, image: Image.Image, queries: list[str], threshold: float) -> list[dict]:
        # Primary tek başına; gerektiğinde fallback adayları ayrı inference'a verilir.
        text_labels = [queries]
        inputs = self.processor(
            text=text_labels, images=image, return_tensors="pt"
        )
        if self.device != "cpu":
            inputs = inputs.to(self.device)

        # Eğitim yapılmadığından gradyan hesaplamaya gerek yoktur.
        with torch.inference_mode():
            outputs = self.model(**inputs)

        # Kutuları orijinal görüntünün piksel boyutlarına dönüştür.
        result = self.processor.post_process_grounded_object_detection(
            outputs=outputs,
            target_sizes=self._target_sizes(image),
            threshold=threshold,
            text_labels=text_labels,
        )[0]

        detections = []
        # Aynı kullanıcı niyetinin adayları ortak label alır; mevcut class-aware NMS
        # farklı İngilizce adaylardan gelen örtüşen kutuları da karşılaştırabilir.
        for box, label, score in zip(
            result["boxes"], result["text_labels"], result["scores"]
        ):
            xmin, ymin, xmax, ymax = box.tolist()
            detections.append(
                {
                    "label": label,
                    "model_query": label,
                    "confidence": score.item(),
                    "box": {
                        "xmin": xmin,
                        "ymin": ymin,
                        "xmax": xmax,
                        "ymax": ymax,
                    },
                }
            )

        # Debug endpoint'i NMS veya containment filtresi olmadan bu kutuları kullanır.
        return detections
