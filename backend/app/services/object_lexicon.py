"""Türkçe nesne adları için kontrollü TR→EN sözlüğü.

Makine çevirisi tek kelimelik, çok anlamlı sorgularda güvenilmez (ör. "yüz" → "100",
"insan" → "human"). Dil tespiti de Türkçe karakter içermeyen kısa sözcüklerde
yanılır (ör. "kravat", "fare" İngilizce sanılır). Bu sözlük, dedektörlerin en iyi
tanıdığı İngilizce karşılığı (çoğunlukla COCO/LVIS sınıf adı) doğrudan verir.
Sözlükte olmayan ifadeler Marian çeviri modeline düşer.
"""

import unicodedata

# Nesne adları. Değerler dedektörlerin eğitimde gördüğü sınıf adlarına yakın seçildi.
OBJECTS = {
    # İnsan ve vücut
    "insan": "person", "kişi": "person", "kisi": "person", "adam": "man", "erkek": "man",
    "kadın": "woman", "çocuk": "child", "bebek": "baby", "yüz": "face", "el": "hand",
    "kafa": "head", "baş": "head", "göz": "eye", "saç": "hair", "ayak": "foot",
    # Giyim ve aksesuar
    "kravat": "tie", "gömlek": "shirt", "tişört": "t-shirt", "ceket": "jacket",
    "takım elbise": "suit", "pantolon": "pants", "etek": "skirt", "elbise": "dress",
    "şapka": "hat", "kask": "helmet", "eldiven": "glove", "ayakkabı": "shoe",
    "spor ayakkabı": "sneakers", "bot": "boot", "çorap": "sock", "kemer": "belt",
    "gözlük": "glasses", "güneş gözlüğü": "sunglasses", "saat": "clock",
    "kol saati": "watch", "kolye": "necklace", "yüzük": "ring", "küpe": "earring",
    "cüzdan": "wallet", "çanta": "bag", "el çantası": "handbag", "sırt çantası": "backpack",
    "laptop çantası": "laptop bag", "valiz": "suitcase", "bavul": "suitcase",
    "şemsiye": "umbrella", "maske": "mask",
    # Taşıtlar ve sokak
    "araba": "car", "otomobil": "car", "otobüs": "bus", "kamyon": "truck",
    "motosiklet": "motorcycle", "motor": "motorcycle", "bisiklet": "bicycle",
    "tren": "train", "uçak": "airplane", "tekne": "boat", "gemi": "ship",
    "tekerlek": "wheel", "lastik": "tire", "trafik ışığı": "traffic light",
    "trafik lambası": "traffic light", "dur işareti": "stop sign", "tabela": "sign",
    "yangın musluğu": "fire hydrant", "bank": "bench", "park bankı": "bench",
    # Hayvanlar
    "köpek": "dog", "kedi": "cat", "kuş": "bird", "at": "horse", "inek": "cow",
    "koyun": "sheep", "fil": "elephant", "ayı": "bear", "zebra": "zebra",
    "zürafa": "giraffe", "balık": "fish", "tavuk": "chicken", "oyuncak ayı": "teddy bear",
    # Mutfak ve yiyecek
    "şişe": "bottle", "su şişesi": "water bottle", "bardak": "cup", "fincan": "cup",
    "kahve fincanı": "coffee cup", "kupa": "mug", "şarap kadehi": "wine glass",
    "kadeh": "wine glass", "tabak": "plate", "kase": "bowl", "çatal": "fork",
    "bıçak": "knife", "kaşık": "spoon", "tencere": "pot", "tava": "pan",
    "elma": "apple", "muz": "banana", "portakal": "orange", "limon": "lemon",
    "havuç": "carrot", "brokoli": "broccoli", "domates": "tomato", "ekmek": "bread",
    "sandviç": "sandwich", "sosisli": "hot dog", "kek": "cake", "turta": "pie",
    "çörek": "donut", "kutu": "box", "karton kutu": "cardboard box", "konserve": "can",
    "teneke kutu": "can", "poşet": "plastic bag", "kavanoz": "jar",
    # Ev eşyası
    "sandalye": "chair", "koltuk": "armchair", "kanepe": "couch", "masa": "table",
    "yemek masası": "dining table", "çalışma masası": "desk", "yatak": "bed",
    "yastık": "pillow", "halı": "rug", "kilim": "rug", "perde": "curtain",
    "lamba": "lamp", "masa lambası": "table lamp", "ayna": "mirror", "kapı": "door",
    "pencere": "window", "dolap": "cabinet", "raf": "shelf", "kitaplık": "bookshelf",
    "saksı": "flower pot", "bitki": "plant", "saksı bitkisi": "potted plant",
    "saksıdaki bitki": "potted plant", "çiçek": "flower", "vazo": "vase",
    "tuvalet": "toilet", "lavabo": "sink", "buzdolabı": "refrigerator",
    "fırın": "oven", "mikrodalga": "microwave", "ekmek kızartma makinesi": "toaster",
    "makas": "scissors", "diş fırçası": "toothbrush", "saç kurutma makinesi": "hair drier",
    "havlu": "towel", "çöp kutusu": "trash can", "kova": "bucket", "mum": "candle",
    # Elektronik ve ofis
    "telefon": "phone", "cep telefonu": "cell phone", "bilgisayar": "computer",
    "dizüstü bilgisayar": "laptop", "laptop": "laptop", "klavye": "keyboard",
    "fare": "mouse", "monitör": "monitor", "ekran": "screen", "televizyon": "tv",
    "kumanda": "remote", "kulaklık": "headphones", "kamera": "camera",
    "fotoğraf makinesi": "camera", "kablo": "cable", "şarj aleti": "charger",
    "kitap": "book", "defter": "notebook", "kalem": "pen", "kurşun kalem": "pencil",
    "kağıt": "paper", "zarf": "envelope", "dosya": "folder",
    # Spor ve diğer
    "top": "ball", "futbol topu": "soccer ball", "uçurtma": "kite", "kayak": "skis",
    "kaykay": "skateboard", "sörf tahtası": "surfboard", "raket": "tennis racket",
    "beyzbol sopası": "baseball bat", "frizbi": "frisbee", "anahtar": "key",
    "ağaç": "tree", "taş": "stone", "kaya": "rock",
}

# Basit sıfat + isim birleşimleri için (Türkçe ve İngilizce sıra aynı: "kırmızı araba").
MODIFIERS = {
    "kırmızı": "red", "mavi": "blue", "yeşil": "green", "sarı": "yellow",
    "siyah": "black", "beyaz": "white", "gri": "gray", "turuncu": "orange",
    "mor": "purple", "pembe": "pink", "kahverengi": "brown", "lacivert": "navy",
    "büyük": "large", "küçük": "small", "uzun": "long", "kısa": "short",
    "eski": "old", "yeni": "new", "ahşap": "wooden", "metal": "metal",
    "plastik": "plastic", "cam": "glass",
}

_ASCII_FOLD = str.maketrans("çğıöşü", "cgiosu")


def normalize_key(text: str, turkish: bool = True) -> str:
    """NFKC + küçük harf. Türkçe modda I→ı, İ→i; casefold'un eklediği noktayı siler."""
    text = unicodedata.normalize("NFKC", text)
    if turkish:
        text = text.replace("I", "ı").replace("İ", "i")
    return " ".join(text.casefold().replace("̇", "").split())


def _with_ascii_variants(table: dict[str, str], english_words: set[str]) -> dict[str, str]:
    """'canta', 'kirmizi' gibi Türkçe klavyesiz yazımları da kabul et.

    ASCII biçim bir İngilizce sözcükle çakışırsa (ör. 'bot') eklenmez.
    """
    result = dict(table)
    for key, value in table.items():
        folded = key.translate(_ASCII_FOLD)
        if folded != key and folded not in result and folded not in english_words:
            result[folded] = value
    return result


# Sözlükteki İngilizce karşılıklar: bu sözcükler kesin İngilizce kabul edilir.
ENGLISH_VOCABULARY = {
    word for value in (*OBJECTS.values(), *MODIFIERS.values()) for word in [value, *value.split()]
} | {"bags", "rugs", "people", "persons", "men", "women", "cars", "dogs", "cats",
     "bottles", "boxes", "chairs", "plants", "pillows", "object", "thing"}

_OBJECTS = _with_ascii_variants({normalize_key(k): v for k, v in OBJECTS.items()}, ENGLISH_VOCABULARY)
_MODIFIERS = _with_ascii_variants({normalize_key(k): v for k, v in MODIFIERS.items()}, ENGLISH_VOCABULARY)
_PLURAL_SUFFIXES = ("lar", "ler")


def _lookup_object(word: str) -> str | None:
    if word in _OBJECTS:
        return _OBJECTS[word]
    # Çoğul eki yalnızca kök sözlükte varsa atılır: "kravatlar" → "kravat".
    for suffix in _PLURAL_SUFFIXES:
        if word.endswith(suffix) and word[: -len(suffix)] in _OBJECTS:
            return _OBJECTS[word[: -len(suffix)]]
    return None


def lookup(text: str) -> str | None:
    """Tam ifade, çoğul ifade veya 'sıfat(lar) + nesne' eşleşirse İngilizcesini döndür."""
    key = normalize_key(text).strip(".!?,").strip()
    if not key:
        return None
    direct = _lookup_object(key)
    if direct is not None:
        return direct
    words = key.split()
    # Son sözcük(ler) nesne, öncekiler sözlükteki sıfatlar olmalı: "kırmızı spor ayakkabı".
    for split in range(1, len(words)):
        head, tail = words[:split], " ".join(words[split:])
        noun = _lookup_object(tail)
        if noun is not None and all(word in _MODIFIERS for word in head):
            return " ".join([*(_MODIFIERS[word] for word in head), noun])
    return None


def is_known_english(text: str) -> bool:
    words = normalize_key(text, turkish=False).strip(".!?,").split()
    return bool(words) and all(word in ENGLISH_VOCABULARY for word in words)
