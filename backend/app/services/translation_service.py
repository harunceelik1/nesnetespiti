import logging
import re
import unicodedata
from pathlib import Path
from threading import Lock

from .. import config
from . import object_lexicon as lexicon


logger = logging.getLogger(__name__)

# Bağlamla çeviri: tek sözcük belirsizdir ("yüz" → "100"); cümle içinde model nesne
# anlamını seçer ("Fotoğrafta yüz var." → "There's a face in the photo.").
CONTEXT_TEMPLATE = "Fotoğrafta {query} var."
_CONTEXT_PATTERNS = [
    re.compile(r"^there(?:'s| is| are| was| were)\s+(?P<obj>.+?)\s+(?:in|on)\s+(?:the|this|that)\s+(?:photo|photograph|picture|image|photography|pic)\W*$", re.I),
    re.compile(r"^(?:in|on)\s+(?:the|this)\s+(?:photo|photograph|picture|image|photography),?\s+there(?:'s| is| are)\s+(?P<obj>.+?)\W*$", re.I),
    re.compile(r"^(?:the|this)\s+(?:photo|photograph|picture|image)\s+(?:has|shows|contains)\s+(?P<obj>.+?)\W*$", re.I),
]
_LEADING_ARTICLE = re.compile(r"^(?:a|an|the|some|one)\s+", re.I)


def extract_object(sentence: str) -> str | None:
    """Bağlam cümlesinin çevirisinden nesne adını çıkarır; kalıp dışıysa None."""
    sentence = " ".join(sentence.split())
    for pattern in _CONTEXT_PATTERNS:
        match = pattern.match(sentence)
        if match:
            obj = _LEADING_ARTICLE.sub("", match.group("obj").strip())
            # "There is a in the photo." gibi boş kalan nesne kabul edilmez.
            return obj if obj and obj.casefold() not in {"a", "an", "the", "some", "one"} else None
    return None


class TranslationServiceError(RuntimeError):
    """İstemciye açıklanabilir çeviri/dil tespiti hatası."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class TranslationService:
    MODEL_NAME = "Helsinki-NLP/opus-mt-tr-en"
    # Dil tespiti kısa kelimelerde belirsiz olabilir; bu bir çeviri sözlüğü değildir.
    ENGLISH_SHORT_QUERIES = {"bag", "bags", "rug", "rugs", "person", "car", "dog", "cat", "backpack"}

    # "context" (varsayılan) veya "lexicon"; bkz. config.TRANSLATION_STRATEGY.
    strategy = config.TRANSLATION_STRATEGY

    def __init__(self, strategy: str | None = None):
        if strategy is not None:
            self.strategy = strategy
        if self.strategy not in config.TRANSLATION_STRATEGIES:
            raise ValueError(f"Bilinmeyen çeviri yolu: {self.strategy!r} (seçenekler: {config.TRANSLATION_STRATEGIES})")
        self.detector = None
        self._load_error = None
        self._lock = Lock()
        try:
            self._load_resources()
        except Exception as exc:
            self._load_error = exc
            # API açılabilir; çeviri gereken isteklere açıklayıcı 503 verilir.
            logger.error("TR→EN çeviri modeli/dil dedektörü yüklenemedi: %s", exc)

    def _load_resources(self):
        import torch
        from lingua import Language, LanguageDetectorBuilder
        from transformers import MarianMTModel, MarianTokenizer

        self._english, self._turkish = Language.ENGLISH, Language.TURKISH
        self.detector = LanguageDetectorBuilder.from_languages(self._english, self._turkish).build()
        self._torch = torch
        cache_dir = Path(__file__).resolve().parents[3] / ".cache" / "translation"
        self.tokenizer = MarianTokenizer.from_pretrained(self.MODEL_NAME, cache_dir=cache_dir)
        self.model = MarianMTModel.from_pretrained(self.MODEL_NAME, cache_dir=cache_dir)
        self.model.eval()

    # Arayüz Türkçe olduğu için belirsiz sorgular Türkçe kabul edilir. Lingua kısa
    # sözcüklerde kararsızdır ("kravat" EN 0.55, "car" EN 0.53); İngilizce ancak
    # bu güvenin üzerindeyse seçilir. Bilinen İngilizce sözcükler bu kontrole gelmez.
    ENGLISH_MIN_CONFIDENCE = 0.60

    def detect_language(self, text: str) -> str:
        normalized = text.casefold().replace("̇", "")
        if self.strategy == "lexicon":
            if lexicon.lookup(text) is not None:
                return "tr"
            if lexicon.is_known_english(text):
                return "en"
        if normalized in self.ENGLISH_SHORT_QUERIES:
            return "en"
        if any(character in normalized for character in "çğıöşü"):
            return "tr"
        if self.detector is None:
            raise TranslationServiceError("Otomatik dil tespiti yüklenemedi. Backend bağımlılıklarını ve terminalini kontrol edin.")
        english_confidence = self.detector.compute_language_confidence(text, self._english)
        return "en" if english_confidence >= self.ENGLISH_MIN_CONFIDENCE else "tr"

    def translate(self, text: str) -> str:
        if self._load_error is not None:
            raise TranslationServiceError(
                "Türkçe→İngilizce çeviri modeli yüklenemedi. Backend bağımlılıklarını ve Hugging Face erişimini kontrol edin."
            ) from self._load_error
        try:
            # Paylaşılan tokenizer/model eşzamanlı isteklerde de yeniden kullanılır.
            with self._lock, self._torch.inference_mode():
                inputs = self.tokenizer(text, return_tensors="pt", truncation=False)
                if inputs["input_ids"].shape[-1] > self.tokenizer.model_max_length:
                    raise TranslationServiceError("Sorgu çeviri modeli için çok uzun. Daha kısa bir nesne ifadesi yazın.", 422)
                tokens = self.model.generate(**inputs, max_new_tokens=128, num_beams=4, do_sample=False)
                translated = self.tokenizer.decode(tokens[0], skip_special_tokens=True)
            translated = " ".join(translated.split())
            if not translated:
                raise TranslationServiceError("Çeviri modeli boş sonuç üretti. Sorguyu farklı bir ifadeyle tekrar deneyin.")
            return translated
        except TranslationServiceError:
            raise
        except Exception as exc:
            logger.error("TR→EN çeviri işlemi başarısız: %s", exc)
            raise TranslationServiceError("Sorgu İngilizceye çevrilemedi. Backend terminalini kontrol ederek tekrar deneyin.") from exc

    def translate_object(self, text: str) -> tuple[str, str]:
        """Nesne adını bağlam cümlesiyle çevirir. (çeviri, kaynak) döndürür.

        Kaynak "context": nesne cümleden çıkarıldı. "model": çeviri beklenen kalıpta
        değildi, sorgu tek başına çevrildi (daha az güvenilir; arayüz uyarı gösterir).
        """
        sentence = self.translate(CONTEXT_TEMPLATE.format(query=text))
        extracted = extract_object(sentence)
        if extracted is not None:
            return extracted, "context"
        logger.info("Bağlam çevirisi kalıp dışı (%r → %r); düz çeviri kullanılıyor.", text, sentence)
        return self.translate(text), "model"

    def prepare_query(self, original_query: str) -> dict:
        text = " ".join(unicodedata.normalize("NFKC", original_query).split())
        if not text:
            raise TranslationServiceError("Sorgu boş olamaz.", 422)
        # "lexicon" yolunda sözlük önce gelir (eski davranış). "context" yolunda sözlük
        # kullanılmaz; Türkçe sorgu bağlam cümlesiyle çevrilir.
        dictionary_translation = lexicon.lookup(text) if self.strategy == "lexicon" else None
        if dictionary_translation is not None:
            language, translated, source = "tr", dictionary_translation, "lexicon"
        else:
            language = self.detect_language(text)
            translated, source = None, None
            if language == "tr":
                translated, source = self.translate_object(text) if self.strategy == "context" else (self.translate(text), "model")
        # Çevirinin tekil/çoğul biçimi ve niteleyicileri korunur.
        return {
            "original_query": original_query,
            "detected_language": language,
            "translated_query": translated,
            "translation_source": source,
            "primary_query": translated if translated is not None else text,
        }
