"""OWLv2 (OWL-ViT ailesinin 2023 sürümü, Minderer ve ark. "Scaling Open-Vocabulary
Object Detection"). Çıkarım kodu OWL-ViT ile aynıdır; yalnızca model, işlemci ve
kutu ölçeklemesi farklıdır."""

from pathlib import Path

import torch
from PIL import Image
from transformers import Owlv2ForObjectDetection, Owlv2Processor

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

    def _target_sizes(self, image: Image.Image) -> torch.Tensor:
        # OWLv2 görüntüyü sağ/alttan dolgu ile kareye tamamlar; kutular bu kareye
        # göredir. Uzun kenarla ölçeklemek orijinal koordinatları verir.
        side = max(image.height, image.width)
        return torch.tensor([[side, side]])
