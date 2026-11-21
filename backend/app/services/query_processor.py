import unicodedata
import re
from typing import NotRequired, TypedDict

from .translation_service import TranslationService, TranslationServiceError


# Çeviriden bağımsız, küçük ve kontrollü synonym mekanizması.
# Adaylar sadece primary detection hiç kutu üretmediğinde kullanılır.
FALLBACK_QUERIES = {
    "bag": ["handbag", "backpack", "tote bag"],
    "laptop bag": ["computer bag", "laptop case"],
    "computer bag": ["laptop bag", "laptop case"],
}

# Yalnızca açıkça tanımlı, tam sözcük eşleşmeleri dönüştürülür. Genel bir "s"
# silme kuralı glass, bus veya scissors gibi sözcükleri yanlış değiştirebilir.
CONTROLLED_SINGULARS = {
    "people": "person",
    "persons": "person",
    "men": "man",
    "women": "woman",
    "bags": "bag",
    "cars": "car",
    "dogs": "dog",
    "cats": "cat",
    "plants": "plant",
    "pillows": "pillow",
    "chairs": "chair",
    "bottles": "bottle",
    "boxes": "box",
}


class ProcessedQuery(TypedDict):
    original_query: str
    detected_language: str
    translated_query: str | None
    primary_query: str
    fallback_queries: list[str]
    processed_query_items: NotRequired[list[dict]]


def _normalize_lookup(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def normalize_primary_query(text: str) -> str:
    """Çeviri sonrası article/noktalama temizliği, ardından kontrollü tekilleştirme."""
    normalized = _normalize_lookup(text).strip().rstrip(".!?").strip()
    normalized = re.sub(r"^(?:the|an|a)\s+", "", normalized)
    # Niteleyiciler, sözcük sırası ve sözlük dışı biçimler aynen korunur.
    return " ".join(CONTROLLED_SINGULARS.get(word, word) for word in normalized.split())


def _combined_source(items: list[dict]) -> str | None:
    sources = {item.get("translation_source") for item in items} - {None}
    return next(iter(sources)) if len(sources) == 1 else ("mixed" if sources else None)


def _fallback_plan(primary_key: str) -> list[str]:
    # Fallback mekanizması çeviriden ve primary normalizasyonundan bağımsızdır.
    candidates = FALLBACK_QUERIES.get(primary_key, [])
    fallback_queries = list(dict.fromkeys(_normalize_lookup(candidate) for candidate in candidates))
    return [candidate for candidate in fallback_queries if candidate != primary_key]


def _combine(original_query: str, items: list[dict]) -> ProcessedQuery:
    """Virgüllü sorgunun parçalarını tek plana birleştirir; aynı primary bir kez sayılır."""
    unique, seen_primary = [], set()
    for item in items:
        if item["primary_query"] and item["primary_query"] not in seen_primary:
            seen_primary.add(item["primary_query"])
            unique.append(item)
    if not unique:
        raise TranslationServiceError("En az bir nesne sorgusu girin.", 422)
    languages = {item["detected_language"] for item in unique}
    return {
        "original_query": original_query,
        "detected_language": next(iter(languages)) if len(languages) == 1 else "mixed",
        "translated_query": ", ".join(item["translated_query"] or item["primary_query"] for item in unique)
        if any(item["translated_query"] is not None for item in unique) else None,
        # Her parçanın kaynağı processed_query_items içinde ayrıca bulunur.
        "translation_source": _combined_source(unique),
        "primary_query": ", ".join(item["primary_query"] for item in unique),
        "fallback_queries": [], "processed_query_items": unique,
    }


def _split_parts(text: str) -> list[str]:
    parts, seen = [], set()
    for part in text.split(","):
        part = " ".join(part.split())
        lookup = _normalize_lookup(part)
        if lookup and lookup not in seen:
            seen.add(lookup)
            parts.append(part)
    return parts


def _override_item(original_part: str, english_part: str) -> dict:
    """Kullanıcının elle yazdığı İngilizce ifade: çeviri atlanır, etiket Türkçe kalır."""
    primary_key = normalize_primary_query(english_part)
    if not primary_key:
        raise TranslationServiceError("Geçerli bir İngilizce nesne ifadesi girin.", 422)
    return {
        "original_query": original_part,
        "detected_language": "user",
        "translated_query": english_part,
        "translation_source": "user",
        "primary_query": primary_key,
        "fallback_queries": _fallback_plan(primary_key),
    }


def process_query(original_query: str, translation_service: TranslationService, english_query: str | None = None) -> ProcessedQuery:
    """Sorguyu modele gidecek İngilizce plana çevirir.

    english_query verilirse (arayüzdeki "Aranan ifade" düzeltmesi) çeviri yapılmaz;
    virgüllü sorguda parça sayıları eşleşmelidir.
    """
    if english_query is not None and english_query.strip():
        originals, englishes = _split_parts(original_query), _split_parts(english_query)
        if len(englishes) == 1 and len(originals) <= 1:
            label = originals[0] if originals else englishes[0]
            return _override_item(label, englishes[0])
        if len(originals) != len(englishes):
            raise TranslationServiceError(
                f"İngilizce ifade sayısı ({len(englishes)}) sorgu sayısıyla ({len(originals)}) aynı olmalı; virgülle ayırın.", 422)
        return _combine(original_query, [_override_item(o, e) for o, e in zip(originals, englishes)])
    if "," in original_query:
        return _combine(original_query, [process_query(part, translation_service) for part in _split_parts(original_query)])
    result = translation_service.prepare_query(original_query)
    primary_key = normalize_primary_query(result["primary_query"])
    if not primary_key:
        raise TranslationServiceError("Geçerli bir nesne sorgusu girin.", 422)
    return {
        **result,
        # translated_query modelin gerçek çıktısı olarak debug için korunur.
        "primary_query": primary_key,
        "fallback_queries": _fallback_plan(primary_key),
    }
