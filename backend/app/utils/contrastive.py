"""Karşıt (contrastive) sorgu: olmayan nesnenin uydurulmasını engeller.

Açık sözlük dedektörler tek sorguda o sözcüğe en çok benzeyen bölgeyi her zaman
bulur: resimde köpek yoksa adamı "dog" diye işaretler. Sorguya görüntüde sık
geçen başka sınıflar (karşıt sorgular) eklenince her kutu en iyi eşleşen sınıfa
atanır; adam "person" olur. Sonra yalnızca kullanıcının sorduğu etiketler tutulur.

Karşıt sorgu, kullanıcının sorgusunu yutabilecek yakın kavramları içermemelidir
(ör. "man" sorgusunda "person" karşıt olursa adamlar person'a gider). Bu yüzden
RELATED tablosundaki ilişkili sınıflar o sorgu için çıkarılır.
"""

from .. import config
from ..config import ContrastiveQuerySettings


def _key(label: str) -> str:
    # DINO decode'u "t-shirt" → "t - shirt" gibi boşluk ekleyebilir.
    return "".join(ch for ch in label.casefold() if ch.isalnum())


def _related(query: str, settings: ContrastiveQuerySettings) -> set[str]:
    words = set(query.casefold().split())
    blocked = set()
    for group in settings.related_groups:
        # Sorgunun kendisi veya son sözcüğü ("red car" → car) gruptaysa tüm grup çıkarılır.
        if query.casefold() in group or (words and query.casefold().split()[-1] in group):
            blocked |= set(group)
    return blocked


def contrastive_queries(queries: list[str], settings: ContrastiveQuerySettings | None = None) -> list[str]:
    """Sorgulara eklenecek karşıt sınıflar; sorgularla çakışan veya ilişkili olanlar hariç."""
    settings = settings if settings is not None else config.CONTRASTIVE_QUERIES
    if not settings.enabled or not queries:
        return []
    # Genel sorgu ("product") her nesneyi kapsar: karşıt sınıf eklemek doğru
    # kutuları yanlış sınıfa kaçırır.
    if any(" ".join(query.casefold().split()) in settings.generic_queries for query in queries):
        return []
    blocked = {_key(query) for query in queries}
    for query in queries:
        blocked |= {_key(item) for item in _related(query, settings)}
        # "coffee cup" sorgusunda "cup" karşıt olamaz: sorgunun sözcükleri de engellenir.
        blocked |= {_key(word) for word in query.split()}
    return [item for item in settings.distractors if _key(item) not in blocked]


def keep_requested(detections: list[dict], queries: list[str]) -> list[dict]:
    """Yalnızca sorulan sınıfa atanmış kutuları tut; karşıt sınıf kutuları atılır."""
    requested = {_key(query): query for query in queries}
    kept = []
    for detection in detections:
        query = requested.get(_key(detection["label"]))
        if query is not None:
            kept.append({**detection, "label": query, "model_query": query})
    return kept
