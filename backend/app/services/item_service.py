"""
Item normalization, duplicate detection, and spelling correction.

Handles:
- Normalization: lowercase, strip, singularize
- Canonical mapping: regional/alternate names → US-English canonical
- Exact duplicate detection (same user + week)
- Near-duplicate / fuzzy matching ("tumeric" vs "turmeric")
- Spelling suggestions from a known veggie list
"""
import re
from difflib import SequenceMatcher, get_close_matches
from typing import Optional

# Common plant foods — seeded list; grows as users add new items.
# Always use the canonical form here (same as CANONICAL_MAPPINGS values).
KNOWN_ITEMS = sorted(set([
    "acai", "acorn squash", "alfalfa sprout", "almond", "amaranth",
    "apple", "apricot", "artichoke", "arugula", "asparagus",
    "avocado", "banana", "barley", "basil", "beet",
    "bell pepper", "blackberry", "black bean", "black pepper",
    "blueberry", "bok choy", "brazil nut", "broccoli", "brown rice",
    "brussels sprout", "buckwheat", "butternut squash", "cabbage", "cacao",
    "cantaloupe", "caper", "cardamom", "carrot", "cashew",
    "cauliflower", "cayenne pepper", "celery", "chamomile", "chard",
    "cherry", "chia seed", "chickpea", "chili pepper", "chive",
    "chlorophyll", "cilantro", "cinnamon", "clove", "coconut",
    "collard green", "coriander", "corn", "cranberry", "cucumber",
    "cumin", "currant", "daikon", "date", "dill",
    "pitaya", "edamame", "eggplant", "elderberry", "endive",
    "farro", "fava bean", "fennel", "fig", "flax seed", "frisee", "garlic",
    "ginger", "goji berry", "grape", "grapefruit", "green bean",
    "green onion", "green pea", "guava", "habanero", "hazelnut",
    "hemp seed", "honeydew", "jackfruit", "jalapeno", "jerusalem artichoke", "jicama",
    "kale", "kidney bean", "kiwi", "kohlrabi", "kombu",
    "lavender", "leek", "lemon", "lemongrass", "lentil",
    "lettuce", "lima bean", "lime", "lychee", "macadamia nut",
    "mache", "mandarin", "mango", "maple syrup", "marjoram", "matcha", "melon",
    "mint", "miso", "moringa", "mushroom", "mustard",
    "nectarine", "nori", "nutmeg", "oat", "okra",
    "olive", "onion", "orange", "oregano", "papaya",
    "paprika", "parsley", "parsnip", "passion fruit", "peach",
    "peanut", "pear", "pecan", "pepper", "persimmon",
    "pine nut", "pineapple", "pistachio", "plantain", "plum",
    "pluot", "pomegranate", "poppy seed", "potato", "pumpkin",
    "pumpkin seed", "quinoa", "radicchio", "radish", "raisin",
    "raspberry", "red cabbage", "red pepper", "rhubarb", "rice",
    "romaine", "rosemary", "rutabaga", "saffron", "sage",
    "sauerkraut", "scallion", "sesame seed", "shallot", "shiitake mushroom",
    "shiso", "snap pea", "snow pea", "soy bean", "spinach", "spirulina",
    "squash", "star anise", "strawberry", "sugar snap pea", "sunflower seed",
    "sweet potato", "swiss chard", "tangerine", "tarragon", "tempeh",
    "thyme", "tofu", "tomatillo", "tomato", "turmeric",
    "turnip", "vanilla", "wakame", "walnut", "wasabi",
    "watercress", "watermelon", "wheat", "wild rice", "yam", "yerba mate", "zucchini",
]))

# ---------------------------------------------------------------------------
# Canonical name mapping
# ---------------------------------------------------------------------------
# Each sub-dict covers one category of variant → canonical (US-English) name.
# Add new entries to the appropriate sub-dict; CANONICAL_MAPPINGS merges them.
#
# When a user types any of the left-hand keys, their entry is stored under
# the right-hand canonical name — keeping tallies clean across all users.

# ── Regional / alternate names (US-English canonical chosen) ──────────────
_REGIONAL_NAMES: dict[str, str] = {
    "rucola":                   "arugula",
    "aubergine":                "eggplant",
    "pak choi":                 "bok choy",
    "pakchoi":                  "bok choy",
    "dragon fruit":             "pitaya",
    "dragonfruit":              "pitaya",
    "garbanzo bean":            "chickpea",
    "kaki":                     "persimmon",
    "kurkuma":                  "turmeric",   # German / Polish
    "curcuma":                  "turmeric",   # French / Italian / Latin scientific name
    "cúrcuma":                  "turmeric",   # Spanish / Portuguese (accent on ú)
    "koriander":                "coriander",
    "basilicum":                "basil",
    "basilicum spice":          "basil",
    "açaí":                     "acai",
    "jalapeño":                 "jalapeno",
    "jalepeno":                 "jalapeno",
    "yerba maté":               "yerba mate",
    "frisée":                   "frisee",
}

# ── Alternate spellings / form variations ─────────────────────────────────
_ALTERNATE_SPELLINGS: dict[str, str] = {
    "chilli":                   "chili",
    "chilli flake":             "chili flake",
    "red chilli":               "red chili",
    "red chilli pepper":        "red chili pepper",
    "paprika powder":           "paprika",
    "smoked paprika powder":    "smoked paprika",
    "lemon grass":              "lemongrass",
    "passionfruit":             "passion fruit",
    "flaxseed":                 "flax seed",
    "microgreen":               "micro green",
    "beansprout":               "bean sprout",
    "soybean":                  "soy bean",
    "blackcurrant":             "black currant",
    "blackurrant":              "black currant",
    "redcurrant":               "red currant",
    "zaatar":                   "za'atar",
    "bulgar":                   "bulgur",
    "bulgar wheat":             "bulgur",
    "bulgur wheat":             "bulgur",
    "cous cous":                "couscous",
    "cuscous":                  "couscous",
    "wakame seaweed":           "wakame",
    "kombu seaweed":            "kombu",
    "shiitake":                 "shiitake mushroom",
    "shiso leaf":               "shiso",
    "mandarine":                "mandarin",
    "pecan nut":                "pecan",
    "cashew nut":               "cashew",
    "rosmaryn":                 "rosemary",
    "miso paste":               "miso",
}

# ── Persistent common typos (appeared 5+ times historically) ──────────────
_COMMON_TYPOS: dict[str, str] = {
    "tomatoe":                  "tomato",
    "cherry tomatoe":           "cherry tomato",
    "sweet potatoe":            "sweet potato",
    "potatoe":                  "potato",
    "algea":                    "algae",
    "ashwaganda":               "ashwagandha",
    "ashwaghanda":              "ashwagandha",
    "chlorofil":                "chlorophyll",
    "chlorophyl":               "chlorophyll",
    "corriander":               "coriander",
    "kohlaribi":                "kohlrabi",
    "pumkin seed":              "pumpkin seed",
}

# ── British English / European alternatives ───────────────────────────────
_BRITISH_EUROPEAN: dict[str, str] = {
    "courgette":                "zucchini",
    "beetroot":                 "beet",
    "rocket":                   "arugula",
    "spring onion":             "green onion",
    "swede":                    "rutabaga",
    "broad bean":               "fava bean",
    "runner bean":              "green bean",
    "french bean":              "green bean",
    "mangetout":                "snow pea",
    "mange tout":               "snow pea",
    "cos":                      "romaine",
    "cos lettuce":              "romaine",
    "sharon fruit":             "persimmon",
    "clementine":               "mandarin",
    "satsuma":                  "mandarin",
    "bok choi":                 "bok choy",
    "capsicum":                 "bell pepper",
    "topinambur":               "jerusalem artichoke",
    "feldsalat":                "mache",
    "mâche":                    "mache",
}

# ── Polish names / spellings ──────────────────────────────────────────────
_POLISH_NAMES: dict[str, str] = {
    "rukola":                   "arugula",
    "cukinia":                  "zucchini",
    "burak":                    "beet",
    "kolendra":                 "coriander",
    "rozmaryn":                 "rosemary",
    "borowka":                  "blueberry",
    "borówka":                  "blueberry",
    "malina":                   "raspberry",
    "kalafior":                 "cauliflower",
    "brokoli":                  "broccoli",
    "koliander":                "coriander",
}

# Combined mapping — merges all categories above.
CANONICAL_MAPPINGS: dict[str, str] = {
    **_REGIONAL_NAMES,
    **_ALTERNATE_SPELLINGS,
    **_COMMON_TYPOS,
    **_BRITISH_EUROPEAN,
    **_POLISH_NAMES,
}

# Display-name overrides for canonical forms that need special characters
# restored (e.g. accented chars stripped during normalization).
# Key = item_name_normalized (no accents), value = display form (with accents).
_DISPLAY_OVERRIDES: dict[str, str] = {
    "jalapeno":   "jalapeño",   # restore ñ
    "acai":       "açaí",       # restore ç and í
    "yerba mate": "yerba maté", # restore é
    "frisee":     "frisée",     # restore é
    "mache":      "mâche",      # restore â
}


def _normalize_raw(name: str) -> str:
    """Lowercase, strip, singularize — does NOT apply canonical mapping."""
    name = name.strip().lower()
    name = re.sub(r'[.,;:!?]+$', '', name)
    name = _singularize(name)
    return name


def normalize_item(name: str) -> str:
    """
    Full normalization pipeline: strip → lowercase → singularize → canonical map.
    Returns the canonical normalized name for storage and deduplication.
    """
    raw = _normalize_raw(name)
    return CANONICAL_MAPPINGS.get(raw, raw)


def get_display_name(name: str) -> str:
    """
    Returns the display name to store in item_name.
    - Mapped items:     returns the canonical name (already lowercase), then
                        checks _DISPLAY_OVERRIDES to restore any special chars.
    - Non-mapped items: returns the input stripped and lowercased, then also
                        checks _DISPLAY_OVERRIDES — so typing "jalapeno" (no
                        accent) still stores "jalapeño".
    We do NOT singularize the display name — that is only done for item_name_normalized.
    This keeps item_name consistent with the DB convention (always lowercase).
    """
    raw = _normalize_raw(name)
    canonical = CANONICAL_MAPPINGS.get(raw)
    if canonical is not None:
        return _DISPLAY_OVERRIDES.get(canonical, canonical)
    return _DISPLAY_OVERRIDES.get(raw, name.strip().lower())


def _singularize(word: str) -> str:
    """Simple English singularization for food items."""
    if len(word) <= 3:
        return word

    if word.endswith("ies") and len(word) > 4:
        # berries → berry, cherries → cherry
        return word[:-3] + "y"
    elif word.endswith("aves"):
        # leaves → leaf, loaves → loaf
        return word[:-4] + "af"
    elif word.endswith("ves"):
        # olives → olive, cloves → clove, chives → chive
        # (just strip the 's' — the 'v' belongs to the stem)
        return word[:-1]
    elif word.endswith("ses") and not word.endswith("ases"):
        return word
    elif word.endswith("es") and word[-3] not in "aeiou":
        # tomatoes → tomato, potatoes → potato
        candidate = word[:-2]
        if candidate.endswith("to") or candidate.endswith("o"):
            return candidate
        return word[:-1] if word.endswith("es") else word
    elif word.endswith("s") and not word.endswith("ss") and not word.endswith("us"):
        return word[:-1]

    return word


def check_spelling(item: str) -> Optional[str]:
    """
    Check if the item might be misspelled and suggest a correction.
    Returns None if it looks fine, or a suggestion string.
    """
    normalized = normalize_item(item)  # includes canonical mapping

    if normalized in KNOWN_ITEMS:
        return None

    matches = get_close_matches(normalized, KNOWN_ITEMS, n=1, cutoff=0.75)
    if matches:
        return matches[0]

    return None


def find_near_duplicate(normalized_item: str, existing_items: list[str]) -> Optional[str]:
    """
    Check if the normalized item is a near-duplicate of any existing item.
    Returns the near-match string, or None.
    """
    for existing in existing_items:
        if existing == normalized_item:
            continue
        ratio = SequenceMatcher(None, normalized_item, existing).ratio()
        if ratio >= 0.80:
            return existing

    return None
