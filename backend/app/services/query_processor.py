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


def process_query(original_query: str, translation_service: TranslationService) -> ProcessedQuery:
    """Model tabanlı çeviri sonucuna bağımsız bir fallback planı ekler."""
    if "," in original_query:
        items, seen_parts, seen_primary = [], set(), set()
        for part in original_query.split(","):
            part = " ".join(part.split())
            lookup = _normalize_lookup(part)
            if not lookup or lookup in seen_parts:
                continue
            seen_parts.add(lookup)
            item = process_query(part, translation_service)
            if item["primary_query"] and item["primary_query"] not in seen_primary:
                seen_primary.add(item["primary_query"])
                items.append(item)
        if not items:
            raise TranslationServiceError("En az bir nesne sorgusu girin.", 422)
        languages = {item["detected_language"] for item in items}
        return {
            "original_query": original_query,
            "detected_language": next(iter(languages)) if len(languages) == 1 else "mixed",
            "translated_query": ", ".join(item["translated_query"] or item["primary_query"] for item in items)
            if any(item["translated_query"] is not None for item in items) else None,
            # Her parçanın kaynağı processed_query_items içinde ayrıca bulunur.
            "translation_source": _combined_source(items),
            "primary_query": ", ".join(item["primary_query"] for item in items),
            "fallback_queries": [], "processed_query_items": items,
        }
    result = translation_service.prepare_query(original_query)
    primary_key = normalize_primary_query(result["primary_query"])
    if not primary_key:
        raise TranslationServiceError("Geçerli bir nesne sorgusu girin.", 422)
    candidates = FALLBACK_QUERIES.get(primary_key, [])
    # Fallback mekanizması çeviriden ve primary normalizasyonundan bağımsızdır.
    fallback_queries = list(dict.fromkeys(_normalize_lookup(candidate) for candidate in candidates))
    return {
        **result,
        # translated_query modelin gerçek çıktısı olarak debug için korunur.
        "primary_query": primary_key,
        "fallback_queries": [candidate for candidate in fallback_queries if candidate != primary_key],
    }
