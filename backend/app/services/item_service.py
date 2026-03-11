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
    "farro", "fennel", "fig", "flax seed", "garlic",
    "ginger", "goji berry", "grape", "grapefruit", "green bean",
    "green onion", "green pea", "guava", "habanero", "hazelnut",
    "hemp seed", "honeydew", "jackfruit", "jalapeno", "jicama",
    "kale", "kidney bean", "kiwi", "kohlrabi", "kombu",
    "lavender", "leek", "lemon", "lemongrass", "lentil",
    "lettuce", "lima bean", "lime", "lychee", "macadamia nut",
    "mango", "maple syrup", "marjoram", "matcha", "melon",
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
    "shiso", "snap pea", "soy bean", "spinach", "spirulina",
    "squash", "star anise", "strawberry", "sugar snap pea", "sunflower seed",
    "sweet potato", "swiss chard", "tangerine", "tarragon", "tempeh",
    "thyme", "tofu", "tomatillo", "tomato", "turmeric",
    "turnip", "vanilla", "wakame", "walnut", "wasabi",
    "watercress", "watermelon", "wheat", "wild rice", "yam", "zucchini",
]))

# ---------------------------------------------------------------------------
# Canonical name mapping
# ---------------------------------------------------------------------------
# Maps normalized variant → canonical normalized name.
# Covers three cases:
#   1. Regional / alternate names  (rucola → arugula, aubergine → eggplant …)
#   2. Form variations             (passionfruit → passion fruit, shiitake → shiitake mushroom …)
#   3. Persistent common typos     (tomatoe → tomato, potatoe → potato …)
#
# When a user types any of the left-hand keys, their entry is stored under
# the right-hand canonical name — keeping tallies clean across all users.
CANONICAL_MAPPINGS: dict[str, str] = {
    # ── Regional / alternate names (US-English canonical chosen) ──────────
    "rucola":                   "arugula",
    "aubergine":                "eggplant",
    "pak choi":                 "bok choy",
    "pakchoi":                  "bok choy",
    "dragon fruit":             "pitaya",
    "dragonfruit":              "pitaya",
    "garbanzo bean":            "chickpea",
    "kaki":                     "persimmon",
    "kurkuma":                  "turmeric",
    "koriander":                "coriander",
    "basilicum":                "basil",
    "basilicum spice":          "basil",
    "açaí":                     "acai",
    "jalapeño":                 "jalapeno",
    "jalepeno":                 "jalapeno",

    # ── Alternate spellings / form variations ─────────────────────────────
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

    # ── Persistent common typos (appeared 5+ times historically) ──────────
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

# Display-name overrides for canonical forms that need special characters
# restored (e.g. accented chars stripped during normalization).
_DISPLAY_OVERRIDES: dict[str, str] = {
    "jalapeno": "jalapeño",  # restore accent mark
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
    - Mapped items:     returns the canonical name (already lowercase).
    - Non-mapped items: returns the input stripped and lowercased.
    We do NOT singularize the display name — that is only done for item_name_normalized.
    This keeps item_name consistent with the DB convention (always lowercase).
    """
    raw = _normalize_raw(name)
    canonical = CANONICAL_MAPPINGS.get(raw)
    if canonical is not None:
        return _DISPLAY_OVERRIDES.get(canonical, canonical)
    return name.strip().lower()


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
