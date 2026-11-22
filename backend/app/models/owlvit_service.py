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

        # OWLv2'nin objectness başlığı: "bu kutuda gerçekten bir nesne var mı" (0-1).
        # Post-process ile aynı maske (en iyi sınıf puanı > eşik) aynı sırayı verir.
        objectness = [None] * len(result["scores"])
        if isinstance(getattr(outputs, "objectness_logits", None), torch.Tensor):
            keep = torch.sigmoid(outputs.logits[0].max(dim=-1).values) > threshold
            kept = torch.sigmoid(outputs.objectness_logits[0])[keep].tolist()
            if len(kept) == len(objectness):
                objectness = kept

        detections = []
        # Aynı kullanıcı niyetinin adayları ortak label alır; mevcut class-aware NMS
        # farklı İngilizce adaylardan gelen örtüşen kutuları da karşılaştırabilir.
        for box, label, score, object_score in zip(
            result["boxes"], result["text_labels"], result["scores"], objectness
        ):
            xmin, ymin, xmax, ymax = box.tolist()
            detections.append(
                {
                    "label": label,
                    "model_query": label,
                    "confidence": score.item(),
                    **({"objectness": object_score} if object_score is not None else {}),
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

    # ---- Örnekle arama (image-guided / one-shot) ----------------------------------

    def example_candidates(self, image: Image.Image, example_box: dict) -> tuple[list[dict], dict]:
        """Görseldeki her aday kutu için örneğe benzerlik puanı (eşiksiz, NMS'siz).

        Kullanıcının çizdiği kutuya en çok örtüşen model kutusunun sınıf gömüsü sorgu
        olur; diğer tüm kutular bu gömüyle OWL'un kendi sınıf başlığından puanlanır.
        Transformers'ın post_process_image_guided_detection'ı puanları en iyi kutuya
        göre ölçekler (en iyi kutu hep 1.0); "yoksa çizme" için mutlak sigmoid kullanılır.
        Dönüş: (adaylar, seçilen_örnek_kutusu).
        """
        inputs = self.processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)
        with torch.inference_mode():
            feature_map = self.model.image_embedder(pixel_values=pixel_values)[0]
            batch, height, width, dim = feature_map.shape
            image_feats = feature_map.reshape(batch, height * width, dim)
            boxes = self.model.box_predictor(image_feats, feature_map)[0]  # cx, cy, w, h (0-1)
            _, class_embeds = self.model.class_predictor(image_feats)

            scale_h, scale_w = (float(v) for v in self._target_sizes(image)[0])
            corners = torch.stack([boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2,
                                   boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2], dim=1)
            corners = corners * torch.tensor([scale_w, scale_h, scale_w, scale_h], device=corners.device)
            target = torch.tensor([[example_box["xmin"], example_box["ymin"],
                                    example_box["xmax"], example_box["ymax"]]], device=corners.device)
            embeds = class_embeds[0] / (class_embeds[0].norm(dim=-1, keepdim=True) + 1e-6)
            # Makaledeki/HF'deki kural: çizilen kutuyla en iyi örtüşmenin %80'ine yakın
            # kutular arasından görüntü ortalamasına (arka plana) en az benzeyeni seç.
            # En çok örtüşen kutuyu almaya göre RPC'de F1 0.52 → 0.68 (evaluation/exemplar_eval.py).
            ious = _box_iou(target, corners)[0]
            close = (ious >= ious.max() * 0.8).nonzero()[:, 0]
            best = int(close[torch.argmin(embeds[close] @ embeds.mean(dim=0))])
            similarity = (embeds @ embeds[best]).cpu()
            if hasattr(self.model, "objectness_predictor"):  # yalnızca OWLv2
                objectness = torch.sigmoid(self.model.objectness_predictor(image_feats)[0]).cpu()
            else:
                objectness = torch.ones_like(similarity)

        corners = corners.cpu().tolist()
        candidates = [{"confidence": float(s), "similarity": float(s), "objectness": float(o), "box": _as_box(box)}
                      for s, o, box in zip(similarity.tolist(), objectness.tolist(), corners)]
        return candidates, _as_box(corners[best])


def _as_box(values) -> dict:
    xmin, ymin, xmax, ymax = (float(v) for v in values)
    return {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}


def _box_iou(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    top_left = torch.max(a[:, None, :2], b[None, :, :2])
    bottom_right = torch.min(a[:, None, 2:], b[None, :, 2:])
    intersection = (bottom_right - top_left).clamp(min=0).prod(dim=2)
    area_a = (a[:, 2:] - a[:, :2]).clamp(min=0).prod(dim=1)
    area_b = (b[:, 2:] - b[:, :2]).clamp(min=0).prod(dim=1)
    return intersection / (area_a[:, None] + area_b[None, :] - intersection).clamp(min=1e-9)
