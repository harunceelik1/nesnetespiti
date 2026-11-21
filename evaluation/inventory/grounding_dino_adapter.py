"""Evaluation-only Grounding DINO phrase çözümleme; fuzzy matching yapmaz."""

import unicodedata


def phrase_tokens(label: str) -> tuple[str, ...]:
    # Noktalama sınırlarını boşluk yap; kelime sırasını ve diğer token'ları koru.
    text = "".join(" " if unicodedata.category(char).startswith("P") else char
                   for char in label.lower().strip())
    tokens = text.split()
    # Yalnızca bitişik aynı token tekrarları: 'drink drink' -> 'drink'.
    # Token silme, substring, edit-distance veya kelime sırası tahmini yoktur.
    return tuple(token for index, token in enumerate(tokens) if not index or token != tokens[index - 1])


def build_caption(prompts: list[str]) -> str:
    """Servisin candidate-list girişini HF processor bu noktalı caption'a çevirir."""
    if not prompts or any(not prompt.strip() or "." in prompt for prompt in prompts):
        raise ValueError("Grounding DINO candidate prompt'ları boş veya nokta içeren phrase olamaz.")
    return ". ".join(prompt.strip().lower() for prompt in prompts) + "."


def resolve_label(label: str, mapping: dict[str, str]) -> tuple[str, str] | None:
    """Model phrase -> tek güvenli model prompt -> canonical kategori."""
    tokens = phrase_tokens(label)
    matches = [(category, prompt) for category, prompt in mapping.items()
               if tokens and phrase_tokens(prompt) == tokens]
    # Normalizasyon iki prompt'u aynı hale getirirse tahmin yürütme.
    return matches[0] if len(matches) == 1 else None
