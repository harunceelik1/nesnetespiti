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


# API'deki "owlvit" yuvasında hangi model çalışır: "v2" (OWLv2, varsayılan) veya "v1".
OWL_VERSION = "v2"


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
        # Masa sahneleri: kutu benzeri büyük nesneler "X box" sorgularını çekiyordu
        # (laptop, "medicine box" için 0.55). Liste uzadıkça DINO skorları seyrelir;
        # yalnızca ölçülerek eklenmeli.
        "laptop", "keyboard", "computer mouse", "book", "tv",
    )
    # Bu genel sorgular tüm ürünleri kapsar; karşıt sınıflar (bottle, cup...)
    # ürün kutularını kendine çekip sonucu boşaltır. Bunlarda karşıt sorgu kapalıdır.
    generic_queries: frozenset[str] = frozenset({
        "product", "products", "item", "items", "object", "objects", "thing", "things",
        "package", "packages", "packet", "goods", "merchandise", "grocery", "groceries",
    })
    # Aynı gruptaki bir sorgu için gruptaki diğer sınıflar karşıt yapılmaz.
    related_groups: tuple[frozenset[str], ...] = (
        frozenset({"person", "man", "woman", "child", "boy", "girl", "baby", "people", "human",
                   "face", "head", "hand", "arm", "leg", "foot", "eye", "hair", "body"}),
        frozenset({"bag", "handbag", "backpack", "tote bag", "laptop bag", "suitcase", "purse", "wallet",
                   "plastic bag", "pouch", "snack", "chips", "snack bag", "noodles", "instant noodles"}),
        frozenset({"cup", "mug", "coffee cup", "glass", "wine glass", "bottle", "water bottle", "can", "jar",
                   "carton", "milk carton", "juice box", "drink", "beverage", "soda", "milk", "tin can"}),
        frozenset({"car", "vehicle", "truck", "bus", "van", "taxi", "wheel", "tire"}),
        frozenset({"chair", "armchair", "couch", "sofa", "bench", "seat", "stool",
                   "table", "desk", "dining table", "furniture"}),
        frozenset({"cell phone", "phone", "smartphone", "mobile phone", "remote"}),
        frozenset({"laptop", "computer", "notebook", "keyboard", "computer mouse", "mouse",
                   "monitor", "screen", "tv", "television", "tablet"}),
        frozenset({"book", "notebook", "magazine", "folder", "paper"}),
        frozenset({"dog", "cat", "animal", "pet", "puppy", "kitten"}),
        frozenset({"bird", "chicken", "duck", "pigeon", "airplane", "kite"}),
        frozenset({"tree", "plant", "potted plant", "flower", "bush"}),
        frozenset({"building", "house", "wall", "window", "door"}),
    )


CONTRASTIVE_QUERIES = ContrastiveQuerySettings()

# Primary sorgu hiçbir şey bulamazsa eş anlamlıları (bag → handbag, backpack) dene.
# Kapalı: bu faz tam olarak nesne yokken çalıştığı için uydurmayı artırıyordu
# (adamın eli "handbag", uzaktaki adam "backpack").
SYNONYM_FALLBACK_ENABLED = False


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
    # False: yalnızca ilk eşik denenir; sonuç yoksa "bulunamadı" döner. Eşiği
    # düşürerek aramak, olmayan nesnede en benzer şeyi (laptop → ilaç kutusu)
    # kabul ettiriyordu. Ölçülen etki için bkz. README "Sabit eşik".
    allow_lowering: bool = False

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


@dataclass(frozen=True)
class ExemplarSearchSettings:
    """Örnekle arama (OWLv2): kullanıcının çizdiği kutuya benzeyenleri bulur.

    Puan, OWL sınıf gömüleri arasındaki kosinüs benzerliğidir (metin sorgusundaki
    sigmoid puanı değil; o ölçek görselden alınan örnekle 0.98+ doyuyordu).
    evaluation/exemplar_eval.py ile 20 RPC kalibrasyon görselinde seçildi:
    diğer kopyaların 28/35'i bulundu, 20 sahte kutu (10'u benzer farklı ürün).
    """

    similarity_threshold: float = 0.88
    # OWLv2 objectness başlığı: parça/boşluk kutularını eler.
    min_objectness: float = 0.10
    nms_iou: float = 0.50
    # Küçük kutu, büyüğün en az bu kadarı içindeyse aynı nesne sayılır (parça kutuları).
    max_containment: float = 0.80
    # Çizilen kutu en az bu kadar piksel olmalı (yanlış tıklama ile tek nokta seçilmesin).
    min_box_side: float = 8.0

    def __post_init__(self):
        for value in (self.similarity_threshold, self.min_objectness, self.nms_iou, self.max_containment):
            if not 0 <= value <= 1:
                raise ValueError("Örnekle arama eşikleri [0, 1] aralığında olmalıdır.")


EXEMPLAR_SEARCH = ExemplarSearchSettings()


ADAPTIVE_THRESHOLDS = {
    # OWL-ViT v1 (ölçüm/karşılaştırma için); üretimde OWL yuvası OWLv2'dir.
    "owlvit": AdaptiveThresholdSettings(thresholds=(0.05, 0.03, 0.02, 0.01)),
    # OWLv2: evaluation/calibrate_threshold.py ile 12 RPC kalibrasyon görseli +
    # 16 olmayan nesne vakasında seçildi. 0.13: envanter F1 0.78 (P 0.76, R 0.81),
    # sahte kutu 0; < 0.08'de sahte kutu başlar, > 0.14'te recall hızla düşer.
    "owlv2": AdaptiveThresholdSettings(thresholds=(0.13,)),
    # OWL-ViT skor ölçeği kullanılmaz. İlk deneme mevcut DINO ayarlarıdır;
    # yalnızca sonuç yoksa/şüpheliyse box eşiği düşer, text eşiği sabit kalır.
    "grounding-dino": AdaptiveThresholdSettings(
        thresholds=(GROUNDING_DINO.box_threshold, 0.30, 0.25),
        text_threshold=GROUNDING_DINO.text_threshold,
    ),
    # YOLO-World: 36 var/yok vakasıyla seçildi (envanter "ürün" sorgusunu anlamadığı
    # için RPC kalibrasyonu kullanılamadı). 0.10: var olan 13/18, olmayan 16/16 boş;
    # olmayan nesnede en yüksek sahte puan 0.046.
    "yolo-world": AdaptiveThresholdSettings(thresholds=(0.10,)),
}
