"""OWLv2 (OWL-ViT ailesinin 2023 sürümü, Minderer ve ark. "Scaling Open-Vocabulary
Object Detection"). Çıkarım kodu OWL-ViT ile aynıdır; yalnızca model, işlemci ve
kutu ölçeklemesi farklıdır."""

import hashlib
from collections import OrderedDict
from pathlib import Path
from threading import Lock

import torch
from PIL import Image
from transformers import Owlv2ForObjectDetection, Owlv2Processor
from transformers.models.owlv2.modeling_owlv2 import Owlv2ObjectDetectionOutput

from .owlvit_service import OwlViTService


class Owlv2Service(OwlViTService):
    # API/arayüz kimliği "owlvit" yuvasıdır; eşik politikası ayrı anahtardan okunur.
    model_id = "owlvit"
    policy_key = "owlv2"
    name = "OWLv2"
    response_model = "OWLv2"
    model_name = "google/owlv2-base-patch16-ensemble"

    def __init__(self):
        cache_dir = Path(__file__).resolve().parents[3] / ".cache" / "owlv2"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = Owlv2Processor.from_pretrained(self.model_name, cache_dir=cache_dir)
        self.model = Owlv2ForObjectDetection.from_pretrained(self.model_name, cache_dir=cache_dir)
        self.model.to(self.device)
        self.model.eval()
        # Görsel tarafı (ViT) sorgudan bağımsızdır ve sürenin neredeyse tamamıdır. Aynı görselde
        # tekrar arama (ifade düzenleme, hassasiyet değiştirme, yedek ifade) yalnızca metin
        # tarafını hesaplar: base modelde ~5 sn → ~0.05 sn. Çıktı model(**inputs) ile birebir aynı.
        self._image_cache: OrderedDict[str, tuple] = OrderedDict()
        self._cache_lock = Lock()

    def _target_sizes(self, image: Image.Image) -> torch.Tensor:
        # OWLv2 görüntüyü sağ/alttan dolgu ile kareye tamamlar; kutular bu kareye
        # göredir. Uzun kenarla ölçeklemek orijinal koordinatları verir.
        side = max(image.height, image.width)
        return torch.tensor([[side, side]])

    _CACHE_SIZE = 2

    def _image_features(self, image: Image.Image) -> tuple:
        key = hashlib.blake2b(image.tobytes(), digest_size=16).hexdigest() + f"{image.size}{image.mode}"
        with self._cache_lock:
            if key in self._image_cache:
                self._image_cache.move_to_end(key)
                return self._image_cache[key]
        pixel_values = self.processor(images=image, return_tensors="pt")["pixel_values"].to(self.device)
        with torch.inference_mode():
            feature_map = self.model.image_embedder(pixel_values=pixel_values)[0]
            batch, height, width, dim = feature_map.shape
            image_feats = feature_map.reshape(batch, height * width, dim)
            features = (image_feats, self.model.objectness_predictor(image_feats),
                        self.model.box_predictor(image_feats, feature_map))
        with self._cache_lock:
            self._image_cache[key] = features
            while len(self._image_cache) > self._CACHE_SIZE:
                self._image_cache.popitem(last=False)
        return features

    def _forward(self, image: Image.Image, text_labels: list[list[str]]):
        """model(**inputs) ile aynı çıktı; görsel özellikleri önbellekten gelir."""
        image_feats, objectness_logits, pred_boxes = self._image_features(image)
        text = self.processor(text=text_labels, return_tensors="pt").to(self.device)
        with torch.inference_mode():
            pooled = self.model.owlv2.text_model(input_ids=text["input_ids"], attention_mask=text["attention_mask"]).pooler_output
            query_embeds = self.model.owlv2.text_projection(pooled)
            query_embeds = query_embeds / torch.linalg.norm(query_embeds, ord=2, dim=-1, keepdim=True)
            count = text["input_ids"].shape[0]
            query_embeds = query_embeds.reshape(1, count, query_embeds.shape[-1])
            query_mask = text["input_ids"].reshape(1, count, -1)[..., 0] > 0
            logits, class_embeds = self.model.class_predictor(image_feats, query_embeds, query_mask)
        return Owlv2ObjectDetectionOutput(logits=logits, pred_boxes=pred_boxes, objectness_logits=objectness_logits,
                                          class_embeds=class_embeds, text_embeds=query_embeds)


class Owlv2LargeService(Owlv2Service):
    """Uygulamanın tek yöntemi: OWLv2 large (ViT-L/14). LVIS nadir ve masa fotoğraflarında
    en iyi ölçülen model (outputs/lvis_olcum/yontem_secimi.md, outputs/masa_olcum/masa_olcum.md).
    Puan ölçeği base modelden farklı olduğu için eşikleri ayrı anahtardadır."""

    policy_key = "owlv2-large"
    name = "OWLv2 large"
    response_model = "OWLv2 large"
    model_name = "google/owlv2-large-patch14-ensemble"
