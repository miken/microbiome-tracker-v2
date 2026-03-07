"""
Unit tests for item normalization, spelling check, and near-duplicate detection.
"""
from backend.app.services.item_service import normalize_item, check_spelling, find_near_duplicate


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


def test_normalize_singularizes_ves():
    assert normalize_item("leaves") == "leaf"


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
