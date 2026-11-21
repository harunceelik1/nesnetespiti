"""Sadece evaluation prompt'ları; semantic GT kategori isimlerini değiştirmez."""


PROMPT_ALIASES = {
    "puffed food": "puffed snack package",
    "dried fruit": "dried fruit package",
    "dried food": "dried food package",
    "instant drink": "instant drink package",
    "instant noodles": "instant noodle package",
    "dessert": "dessert package",
    "drink": "beverage bottle",
    "alcohol": "alcohol bottle",
    "milk": "milk carton",
    "canned food": "canned food can",
    "chocolate": "chocolate package",
    "gum": "chewing gum package",
    "candy": "candy package",
    "seasoner": "seasoning package",
    "personal hygiene": "personal care product",
    "tissue": "tissue pack",
    "stationery": "stationery item",
}


def normalize_prompt(text: str) -> str:
    return " ".join(text.casefold().split()).strip(" .")


def build_prompt_mapping(categories: tuple[str, ...], prompt_mode: str = "canonical") -> dict[str, str]:
    if prompt_mode not in ("canonical", "alias"):
        raise ValueError("prompt_mode canonical veya alias olmalıdır.")
    mapping = {category: PROMPT_ALIASES.get(category, category) if prompt_mode == "alias" else category
               for category in categories}
    if any(not isinstance(prompt, str) or not normalize_prompt(prompt) for prompt in mapping.values()):
        raise ValueError("Prompt boş veya geçersiz olamaz.")
    # Tek model etiketi iki GT sınıfına karşılık gelemez; sessiz eşleme yapılmaz.
    if len({normalize_prompt(prompt) for prompt in mapping.values()}) != len(mapping):
        raise ValueError("İki kategori aynı model prompt'una eşleniyor.")
    return mapping
