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
    assert normalize_item("kurkuma") == "turmeric"
    assert normalize_item("basilicum") == "basil"


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
    # jalapeño gets its accent mark restored (still lowercase)
    assert get_display_name("Jalepeno") == "jalapeño"
    assert get_display_name("jalapeño") == "jalapeño"


def test_get_display_name_preserves_original_when_no_mapping():
    # Non-mapped items: return the user's input as-is (stripped)
    assert get_display_name("Broccoli") == "Broccoli"
    assert get_display_name("  Kale  ") == "Kale"
    assert get_display_name("kimchi") == "kimchi"


# --- check_spelling respects canonical mapping ---

def test_check_spelling_no_warning_for_mapped_variant():
    # "dragon fruit" maps to "pitaya" which is in KNOWN_ITEMS → no spelling warning
    assert check_spelling("dragon fruit") is None
    assert check_spelling("rucola") is None
    assert check_spelling("aubergine") is None


def test_check_spelling_suggests_canonical_for_typo_of_canonical():
    # "pittaya" is a typo of "pitaya" (the canonical), should suggest "pitaya"
    suggestion = check_spelling("pittaya")
    assert suggestion == "pitaya"
