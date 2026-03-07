"""
Item normalization, duplicate detection, and spelling correction.

Handles:
- Normalization: lowercase, strip, singularize
- Exact duplicate detection (same user + week)
- Near-duplicate / fuzzy matching ("tumeric" vs "turmeric")
- Spelling suggestions from a known veggie list
"""
import re
from difflib import SequenceMatcher, get_close_matches
from typing import Optional

# Common plant foods — seeded list; grows as users add new items
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
    "dragon fruit", "edamame", "eggplant", "elderberry", "endive",
    "farro", "fennel", "fig", "flax seed", "garlic",
    "ginger", "goji berry", "grape", "grapefruit", "green bean",
    "green onion", "green pea", "guava", "habanero", "hazelnut",
    "hemp seed", "honeydew", "jackfruit", "jalapeno", "jicama",
    "kale", "kidney bean", "kiwi", "kohlrabi", "kombu seaweed",
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
    "sauerkraut", "scallion", "sesame seed", "shallot", "snap pea",
    "soybean", "spinach", "spirulina", "squash", "star anise",
    "strawberry", "sugar snap pea", "sunflower seed", "sweet potato", "swiss chard",
    "tangerine", "tarragon", "tempeh", "thyme", "tofu",
    "tomatillo", "tomato", "turmeric", "turnip", "vanilla",
    "walnut", "wasabi", "watercress", "watermelon", "wheat",
    "wild rice", "yam", "zucchini",
]))


def normalize_item(name: str) -> str:
    """
    Normalize an item name: strip, lowercase, basic singularization.
    """
    name = name.strip().lower()
    # Remove trailing punctuation
    name = re.sub(r'[.,;:!?]+$', '', name)
    # Basic singularization rules (covering common cases)
    name = _singularize(name)
    return name


def _singularize(word: str) -> str:
    """Simple English singularization for food items."""
    # Don't singularize known compound items or short words
    if len(word) <= 3:
        return word
    
    # Handle common plural patterns
    if word.endswith("ies") and len(word) > 4:
        # berries -> berry, cherries -> cherry
        return word[:-3] + "y"
    elif word.endswith("ves"):
        # olives -> olive (but not all -ves words)
        return word[:-3] + "f"  # leaves -> leaf
    elif word.endswith("ses") and not word.endswith("ases"):
        # This is tricky; skip to avoid breaking "miso" etc.
        return word
    elif word.endswith("es") and word[-3] not in "aeiou":
        # tomatoes -> tomato, potatoes -> potato
        candidate = word[:-2]
        if candidate.endswith("to") or candidate.endswith("o"):
            return candidate
        # Otherwise just strip the 's'
        return word[:-1] if word.endswith("es") else word
    elif word.endswith("s") and not word.endswith("ss") and not word.endswith("us"):
        return word[:-1]
    
    return word


def check_spelling(item: str) -> Optional[str]:
    """
    Check if the item might be misspelled and suggest a correction.
    Returns None if it looks fine, or a suggestion string.
    """
    normalized = normalize_item(item)
    
    # If it's already a known item, no suggestion needed
    if normalized in KNOWN_ITEMS:
        return None
    
    # Find close matches
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
            continue  # Exact match handled separately
        ratio = SequenceMatcher(None, normalized_item, existing).ratio()
        if ratio >= 0.80:
            return existing
    
    return None
