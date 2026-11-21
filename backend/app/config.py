from dataclasses import dataclass


@dataclass(frozen=True)
class GroundingDinoSettings:
    """Deneylerde yalnızca buradan değiştirilecek Grounding DINO ayarları."""

    model_name: str = "IDEA-Research/grounding-dino-tiny"
    box_threshold: float = 0.35
    text_threshold: float = 0.25

    def __post_init__(self):
        if not 0 <= self.box_threshold <= 1 or not 0 <= self.text_threshold <= 1:
            raise ValueError("Grounding DINO eşikleri 0 ile 1 arasında olmalıdır.")


GROUNDING_DINO = GroundingDinoSettings()


@dataclass(frozen=True)
class YoloWorldSettings:
    """YOLO-World (Ultralytics) ayarları; skor ölçeği OWL-ViT/DINO ile kıyaslanmaz."""

    # Küçük (s) v2 ağırlığı CPU'da hızlıdır; daha doğru ama yavaş seçenek: yolov8m-worldv2.pt
    weights: str = "yolov8s-worldv2.pt"
    # Ultralytics'in kendi iç NMS IoU değeri; ardından ortak class-aware NMS (0.60) uygulanır.
    model_nms_iou: float = 0.70
    max_detections: int = 300

    def __post_init__(self):
        if not self.weights.endswith(".pt"):
            raise ValueError("YOLO-World ağırlık dosyası .pt olmalıdır.")
        if not 0 < self.model_nms_iou <= 1:
            raise ValueError("YOLO-World NMS IoU (0, 1] aralığında olmalıdır.")
        if self.max_detections < 1:
            raise ValueError("YOLO-World max_detections pozitif olmalıdır.")


YOLO_WORLD = YoloWorldSettings()


@dataclass(frozen=True)
class SceneBoxFilterSettings:
    """Sadece bariz full-scene kutuları hedefleyen, çözünürlükten bağımsız sınırlar."""

    min_area_ratio: float = 0.90
    border_tolerance_ratio: float = 0.03
    min_near_borders: int = 3
    full_scene_min_area_ratio: float = 0.80
    full_scene_near_borders: int = 4
    axis_scene_min_area_ratio: float = 0.85
    axis_scene_min_near_borders: int = 3
    axis_scene_long_coverage: float = 0.97
    axis_scene_short_coverage: float = 0.80

    def __post_init__(self):
        if not 0 < self.min_area_ratio <= 1:
            raise ValueError("Scene-box alan oranı (0, 1] aralığında olmalıdır.")
        if not 0 <= self.border_tolerance_ratio < 0.5:
            raise ValueError("Scene-box kenar toleransı [0, 0.5) aralığında olmalıdır.")
        if type(self.min_near_borders) is not int or not 1 <= self.min_near_borders <= 4:
            raise ValueError("Scene-box yakın kenar sayısı 1–4 arasında olmalıdır.")
        if not 0 < self.full_scene_min_area_ratio <= self.min_area_ratio:
            raise ValueError("Dört-kenar alan oranı (0, min_area_ratio] aralığında olmalıdır.")
        if type(self.full_scene_near_borders) is not int or self.full_scene_near_borders != 4:
            raise ValueError("Dört-kenar kuralı tam dört kenar gerektirir.")
        if not 0 < self.axis_scene_min_area_ratio <= 1:
            raise ValueError("Eksen scene-box alan oranı (0, 1] aralığında olmalıdır.")
        if type(self.axis_scene_min_near_borders) is not int or not 1 <= self.axis_scene_min_near_borders <= 4:
            raise ValueError("Eksen scene-box yakın kenar sayısı 1–4 arasında olmalıdır.")
        if not 0 < self.axis_scene_short_coverage <= self.axis_scene_long_coverage <= 1:
            raise ValueError("Eksen coverage sınırları 0 < short <= long <= 1 sağlamalıdır.")


SCENE_BOX_FILTER = SceneBoxFilterSettings()


@dataclass(frozen=True)
class ContrastiveQuerySettings:
    """Olmayan nesne uydurmasını önleyen karşıt sorgular (bkz. utils/contrastive.py)."""

    enabled: bool = True
    # Grounding DINO: kutu, sorulan sınıfa en iyi karşıt sınıftan en az bu kadar
    # daha iyi uymalı. Gözlenen: sahte "umbrella" (ayakkabı) farkı 0.07, gerçek
    # jacket/hand farkı >= 0.16. 3 görselden seçildi; daha geniş veriyle ayarlanmalı.
    min_margin: float = 0.10
    # Gündelik görüntülerde en sık görülen, birbirinden ayrık COCO sınıfları.
    distractors: tuple[str, ...] = (
        "person", "car", "dog", "cat", "bird", "chair", "table", "bottle", "cup", "bag",
        "cell phone", "tree", "building",
    )
    # Aynı gruptaki bir sorgu için gruptaki diğer sınıflar karşıt yapılmaz.
    related_groups: tuple[frozenset[str], ...] = (
        frozenset({"person", "man", "woman", "child", "boy", "girl", "baby", "people", "human",
                   "face", "head", "hand", "arm", "leg", "foot", "eye", "hair", "body"}),
        frozenset({"bag", "handbag", "backpack", "tote bag", "laptop bag", "suitcase", "purse", "wallet"}),
        frozenset({"cup", "mug", "coffee cup", "glass", "wine glass", "bottle", "water bottle", "can", "jar"}),
        frozenset({"car", "vehicle", "truck", "bus", "van", "taxi", "wheel", "tire"}),
        frozenset({"chair", "armchair", "couch", "sofa", "bench", "seat", "stool",
                   "table", "desk", "dining table", "furniture"}),
        frozenset({"cell phone", "phone", "smartphone", "mobile phone", "remote"}),
        frozenset({"dog", "cat", "animal", "pet", "puppy", "kitten"}),
        frozenset({"bird", "chicken", "duck", "pigeon", "airplane", "kite"}),
        frozenset({"tree", "plant", "potted plant", "flower", "bush"}),
        frozenset({"building", "house", "wall", "window", "door"}),
    )


CONTRASTIVE_QUERIES = ContrastiveQuerySettings()


@dataclass(frozen=True)
class AdaptiveThresholdSettings:
    """Model başına ayrı eşikler; kalite sınırları nesne doğruluğu garantisi değildir."""

    thresholds: tuple[float, ...]
    text_threshold: float | None = None
    # Envanter sahnelerinde (raf, depo) onlarca gerçek nesne olabilir; eski 8 sınırı
    # 20 şişelik bir rafı "detection_explosion" sayıp boş sonuç döndürüyordu.
    max_raw_detections: int = 300
    max_filtered_detections: int = 60
    max_duplicate_fraction: float = 0.90
    weak_score_multiplier: float = 1.20
    max_weak_fraction: float = 0.80

    def __post_init__(self):
        if not self.thresholds or any(not 0 < value <= 1 for value in self.thresholds):
            raise ValueError("Adaptive eşikler (0, 1] aralığında olmalıdır.")
        if any(a <= b for a, b in zip(self.thresholds, self.thresholds[1:])):
            raise ValueError("Adaptive eşikler kesin azalan sırada olmalıdır.")
        if self.text_threshold is not None and not 0 <= self.text_threshold <= 1:
            raise ValueError("Text threshold [0, 1] aralığında olmalıdır.")
        if self.max_raw_detections < 1 or self.max_filtered_detections < 1:
            raise ValueError("Detection sınırları pozitif olmalıdır.")
        if not 0 <= self.max_duplicate_fraction <= 1 or not 0 <= self.max_weak_fraction <= 1:
            raise ValueError("Oranlar [0, 1] aralığında olmalıdır.")
        if self.weak_score_multiplier < 1:
            raise ValueError("Zayıf skor çarpanı en az 1 olmalıdır.")


ADAPTIVE_THRESHOLDS = {
    "owlvit": AdaptiveThresholdSettings(thresholds=(0.05, 0.03, 0.02, 0.01)),
    # OWL-ViT skor ölçeği kullanılmaz. İlk deneme mevcut DINO ayarlarıdır;
    # yalnızca sonuç yoksa/şüpheliyse box eşiği düşer, text eşiği sabit kalır.
    "grounding-dino": AdaptiveThresholdSettings(
        thresholds=(GROUNDING_DINO.box_threshold, 0.30, 0.25),
        text_threshold=GROUNDING_DINO.text_threshold,
    ),
    # YOLO-World'ün kendi confidence ölçeği; Ultralytics varsayılanı 0.25'ten başlar,
    # sonuç yoksa/şüpheliyse açık sözlük sorguları için kademeli olarak düşer.
    "yolo-world": AdaptiveThresholdSettings(thresholds=(0.25, 0.15, 0.10, 0.05)),
}
