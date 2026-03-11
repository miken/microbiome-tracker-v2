"""
Unit tests for item normalization, spelling check, and near-duplicate detection.
"""
from backend.app.services.item_service import normalize_item, get_display_name, check_spelling, find_near_duplicate


# --- normalize_item ---

def test_normalize_strips_whitespace_and_lowercases():
    assert normalize_item("  Spinach  ") == "spinach"


def test_normalize_strips_trailing_punctuation():
    assert normalize_item("garlic,") == "garlic"
    assert normalize_item("basil.") == "basil"
    assert normalize_item("ginger!") == "ginger"


def test_normalize_singularizes_ies():
    assert normalize_item("blueberries") == "blueberry"
    assert normalize_item("cherries") == "cherry"


def test_normalize_singularizes_plain_s():
    assert normalize_item("walnuts") == "walnut"
    assert normalize_item("almonds") == "almond"


def test_normalize_singularizes_aves_to_af():
    # leaf-type plurals: strip 'aves', add 'af'
    assert normalize_item("leaves") == "leaf"


def test_normalize_singularizes_ves_strips_s_only():
    # Bug fix: olives/cloves/chives should NOT become olif/clof/chif
    assert normalize_item("olives") == "olive"
    assert normalize_item("cloves") == "clove"
    assert normalize_item("chives") == "chive"


def test_normalize_handles_already_singular():
    assert normalize_item("turmeric") == "turmeric"
    assert normalize_item("spinach") == "spinach"


def test_normalize_short_words_unchanged():
    # Words <= 3 chars are not singularized
    assert normalize_item("oat") == "oat"


# --- check_spelling ---

def test_check_spelling_known_item_returns_none():
    assert check_spelling("turmeric") is None
    assert check_spelling("spinach") is None


def test_check_spelling_suggests_correction():
    # "tumeric" is a common misspelling of "turmeric"
    suggestion = check_spelling("tumeric")
    assert suggestion == "turmeric"


def test_check_spelling_unknown_item_no_suggestion():
    # Totally unknown item with no close match
    assert check_spelling("xyzqwerty123") is None


# --- find_near_duplicate ---

def test_find_near_duplicate_detects_fuzzy_match():
    result = find_near_duplicate("tumeric", ["cumin", "turmeric"])
    assert result == "turmeric"


def test_find_near_duplicate_skips_exact_match():
    # Exact matches are skipped; only fuzzy checked
    result = find_near_duplicate("garlic", ["garlic", "ginger"])
    assert result is None


def test_find_near_duplicate_no_match():
    result = find_near_duplicate("garlic", ["spinach", "kale", "broccoli"])
    assert result is None


def test_find_near_duplicate_returns_none_for_empty_list():
    assert find_near_duplicate("spinach", []) is None


# --- canonical mapping via normalize_item ---

def test_normalize_maps_regional_names():
    assert normalize_item("rucola") == "arugula"
    assert normalize_item("Rucola") == "arugula"
    assert normalize_item("aubergine") == "eggplant"
    assert normalize_item("Aubergine") == "eggplant"
    assert normalize_item("pak choi") == "bok choy"
    assert normalize_item("dragon fruit") == "pitaya"
    assert normalize_item("dragonfruit") == "pitaya"
    assert normalize_item("garbanzo beans") == "chickpea"
    assert normalize_item("kaki") == "persimmon"
    assert normalize_item("kurkuma") == "turmeric"   # German / Polish
    assert normalize_item("curcuma") == "turmeric"   # French / Italian / Latin
    assert normalize_item("cúrcuma") == "turmeric"   # Spanish / Portuguese
    assert normalize_item("basilicum") == "basil"


def test_normalize_maps_british_english():
    assert normalize_item("courgette") == "zucchini"
    assert normalize_item("Courgette") == "zucchini"
    assert normalize_item("beetroot") == "beet"
    assert normalize_item("rocket") == "arugula"
    assert normalize_item("spring onion") == "green onion"
    assert normalize_item("swede") == "rutabaga"
    assert normalize_item("broad bean") == "fava bean"
    assert normalize_item("broad beans") == "fava bean"
    assert normalize_item("runner bean") == "green bean"
    assert normalize_item("french bean") == "green bean"
    assert normalize_item("mangetout") == "snow pea"
    assert normalize_item("mange tout") == "snow pea"
    assert normalize_item("cos") == "romaine"
    assert normalize_item("cos lettuce") == "romaine"
    assert normalize_item("sharon fruit") == "persimmon"
    assert normalize_item("clementine") == "mandarin"
    assert normalize_item("satsuma") == "mandarin"
    assert normalize_item("bok choi") == "bok choy"
    assert normalize_item("capsicum") == "bell pepper"
    assert normalize_item("topinambur") == "jerusalem artichoke"
    assert normalize_item("feldsalat") == "mache"
    assert normalize_item("mâche") == "mache"


def test_normalize_maps_polish_names():
    assert normalize_item("rukola") == "arugula"
    assert normalize_item("Rukola") == "arugula"
    assert normalize_item("cukinia") == "zucchini"
    assert normalize_item("burak") == "beet"
    assert normalize_item("kolendra") == "coriander"
    assert normalize_item("rozmaryn") == "rosemary"
    assert normalize_item("borowka") == "blueberry"
    assert normalize_item("borówka") == "blueberry"
    assert normalize_item("malina") == "raspberry"
    assert normalize_item("kalafior") == "cauliflower"
    assert normalize_item("brokoli") == "broccoli"
    assert normalize_item("koliander") == "coriander"


def test_normalize_maps_form_variations():
    assert normalize_item("chilli") == "chili"
    assert normalize_item("Chilli flakes") == "chili flake"
    assert normalize_item("paprika powder") == "paprika"
    assert normalize_item("lemon grass") == "lemongrass"
    assert normalize_item("passionfruit") == "passion fruit"
    assert normalize_item("wakame seaweed") == "wakame"
    assert normalize_item("kombu seaweed") == "kombu"
    assert normalize_item("Shiitake") == "shiitake mushroom"
    assert normalize_item("bulgur wheat") == "bulgur"
    assert normalize_item("couscous") == "couscous"  # canonical, no change
    assert normalize_item("cous cous") == "couscous"


def test_normalize_maps_persistent_typos():
    assert normalize_item("tomatoe") == "tomato"
    assert normalize_item("tomatoes") == "tomato"  # plural + typo path
    assert normalize_item("potatoe") == "potato"
    assert normalize_item("sweet potatoe") == "sweet potato"
    assert normalize_item("chlorofil") == "chlorophyll"
    assert normalize_item("pumkin seeds") == "pumpkin seed"


def test_normalize_unchanged_when_already_canonical():
    assert normalize_item("arugula") == "arugula"
    assert normalize_item("eggplant") == "eggplant"
    assert normalize_item("pitaya") == "pitaya"
    assert normalize_item("chickpea") == "chickpea"
    assert normalize_item("turmeric") == "turmeric"
    assert normalize_item("basil") == "basil"
    assert normalize_item("chili") == "chili"


# --- get_display_name ---

def test_get_display_name_returns_canonical_lowercase_for_mapped_variants():
    # Canonical names are stored lowercase to match phone-keyboard input style
    assert get_display_name("rucola") == "arugula"
    assert get_display_name("Rucola") == "arugula"
    assert get_display_name("aubergine") == "eggplant"
    assert get_display_name("basilicum") == "basil"
    assert get_display_name("chilli") == "chili"
    assert get_display_name("paprika powder") == "paprika"
    assert get_display_name("wakame seaweed") == "wakame"
    assert get_display_name("Shiitake") == "shiitake mushroom"


def test_get_display_name_applies_display_overrides():
    # Accents restored regardless of how the user typed it.
    # jalapeño — via CANONICAL_MAPPINGS path (misspelling/accented variant → canonical → override)
    assert get_display_name("Jalepeno") == "jalapeño"   # CANONICAL_MAPPINGS["jalepeno"] → "jalapeno" → override
    assert get_display_name("jalapeño") == "jalapeño"   # CANONICAL_MAPPINGS["jalapeño"] → "jalapeno" → override
    # jalapeño — via direct _DISPLAY_OVERRIDES path (raw IS the override key)
    assert get_display_name("jalapeno") == "jalapeño"   # _DISPLAY_OVERRIDES["jalapeno"]
    assert get_display_name("Jalapeno") == "jalapeño"   # same, case-insensitive via _normalize_raw
    # açaí — canonical mapping path (accented typed form) and direct path (unaccented)
    assert get_display_name("açaí") == "açaí"           # CANONICAL_MAPPINGS["açaí"] → "acai" → override
    assert get_display_name("acai") == "açaí"           # _DISPLAY_OVERRIDES["acai"]
    assert get_display_name("Acai") == "açaí"           # same, case-insensitive
    # yerba maté — canonical mapping path and direct path
    assert get_display_name("yerba maté") == "yerba maté"  # CANONICAL_MAPPINGS["yerba maté"] → "yerba mate" → override
    assert get_display_name("yerba mate") == "yerba maté"  # _DISPLAY_OVERRIDES["yerba mate"]
    # frisée — canonical mapping path and direct path
    assert get_display_name("frisée") == "frisée"       # CANONICAL_MAPPINGS["frisée"] → "frisee" → override
    assert get_display_name("frisee") == "frisée"       # _DISPLAY_OVERRIDES["frisee"]
    assert get_display_name("Frisee") == "frisée"       # same, case-insensitive
    # mâche — canonical mapping path (accented typed form) and direct path (unaccented)
    assert get_display_name("mâche") == "mâche"         # CANONICAL_MAPPINGS["mâche"] → "mache" → override
    assert get_display_name("mache") == "mâche"         # _DISPLAY_OVERRIDES["mache"]
    assert get_display_name("Mache") == "mâche"         # same, case-insensitive
    # courgette → zucchini (no special chars, but verify canonical is returned)
    assert get_display_name("courgette") == "zucchini"
    assert get_display_name("Courgette") == "zucchini"


def test_get_display_name_lowercases_non_mapped_items():
    # Non-mapped items: strip and lowercase (matches DB convention; display is NOT singularized)
    assert get_display_name("Broccoli") == "broccoli"
    assert get_display_name("  Kale  ") == "kale"
    assert get_display_name("kimchi") == "kimchi"


# --- check_spelling respects canonical mapping ---

def test_check_spelling_no_warning_for_mapped_variant():
    # "dragon fruit" maps to "pitaya" which is in KNOWN_ITEMS → no spelling warning
    assert check_spelling("dragon fruit") is None
    assert check_spelling("rucola") is None
    assert check_spelling("aubergine") is None
    # Accented-character items: all forms normalise to a canonical that is in KNOWN_ITEMS
    assert check_spelling("açaí") is None       # → "acai" ∈ KNOWN_ITEMS
    assert check_spelling("acai") is None       # already canonical
    assert check_spelling("yerba mate") is None # ∈ KNOWN_ITEMS
    assert check_spelling("yerba maté") is None # → "yerba mate" ∈ KNOWN_ITEMS
    assert check_spelling("frisee") is None     # ∈ KNOWN_ITEMS
    assert check_spelling("frisée") is None     # → "frisee" ∈ KNOWN_ITEMS
    # British English
    assert check_spelling("courgette") is None  # → "zucchini" ∈ KNOWN_ITEMS
    assert check_spelling("beetroot") is None   # → "beet" ∈ KNOWN_ITEMS
    assert check_spelling("rocket") is None     # → "arugula" ∈ KNOWN_ITEMS
    assert check_spelling("mangetout") is None  # → "snow pea" ∈ KNOWN_ITEMS
    assert check_spelling("capsicum") is None   # → "bell pepper" ∈ KNOWN_ITEMS
    assert check_spelling("mâche") is None      # → "mache" ∈ KNOWN_ITEMS
    assert check_spelling("mache") is None      # ∈ KNOWN_ITEMS
    # Polish
    assert check_spelling("rukola") is None     # → "arugula" ∈ KNOWN_ITEMS
    assert check_spelling("cukinia") is None    # → "zucchini" ∈ KNOWN_ITEMS
    assert check_spelling("borówka") is None    # → "blueberry" ∈ KNOWN_ITEMS
    assert check_spelling("kalafior") is None   # → "cauliflower" ∈ KNOWN_ITEMS


def test_check_spelling_suggests_canonical_for_typo_of_canonical():
    # "pittaya" is a typo of "pitaya" (the canonical), should suggest "pitaya"
    suggestion = check_spelling("pittaya")
    assert suggestion == "pitaya"
