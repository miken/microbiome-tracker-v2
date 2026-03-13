"""
Tests for email_service.py — weekly summary email assembly and rendering.

All AI calls are mocked; no API keys or AWS credentials needed to run.
"""
import datetime
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.app.models.models import Entry, User, VeggieBenefitsCache, Week
from backend.app.services import email_service
from backend.app.services.auth_service import hash_pin

# Fixed week used across all assembly tests
FIXED_START = datetime.date(2026, 3, 8)   # Sunday
FIXED_END   = datetime.date(2026, 3, 14)  # Saturday

# Patch targets
_SVC = "backend.app.services.email_service"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def week(db_session):
    w = Week(start_date=FIXED_START, end_date=FIXED_END, is_active=True)
    db_session.add(w)
    await db_session.commit()
    await db_session.refresh(w)
    return w


@pytest_asyncio.fixture
async def user_alice(db_session, week):
    """Active user with two plant entries for the fixed week."""
    u = User(name="Alice", pin_hash=hash_pin("1234"), is_active=True)
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    for item, norm in [("kale", "kale"), ("blueberry", "blueberry")]:
        db_session.add(Entry(
            user_id=u.id, week_id=week.id,
            item_name=item, item_name_normalized=norm,
        ))
    await db_session.commit()
    return u


@pytest_asyncio.fixture
async def user_bob(db_session, week):
    """Active user with no entries for the fixed week."""
    u = User(name="Bob", pin_hash=hash_pin("5678"), is_active=True)
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


def _all_ai_patches():
    """Return patch objects for every AI function used in assemble_email_data."""
    return [
        patch(f"{_SVC}.get_current_week_dates", return_value=(FIXED_START, FIXED_END)),
        patch(f"{_SVC}.ai_service.generate_person_praise",            new=AsyncMock(return_value="Great job!")),
        patch(f"{_SVC}.ai_service.generate_gut_quip",                 new=AsyncMock(return_value="Gut gold.")),
        patch(f"{_SVC}.ai_service.generate_veggie_spotlight",         new=AsyncMock(return_value={"fun_fact": "Amazing!", "benefit": "Good for gut."})),
        patch(f"{_SVC}.ai_service.generate_suggestion",               new=AsyncMock(return_value="Try spinach.")),
        patch(f"{_SVC}.ai_service.generate_no_veggies_encouragement", new=AsyncMock(return_value="You got this!")),
    ]


# ---------------------------------------------------------------------------
# assemble_email_data — structure tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assemble_returns_empty_when_no_week(db_session):
    """Returns {} when no Week row exists for the current period."""
    with patch(f"{_SVC}.get_current_week_dates", return_value=(FIXED_START, FIXED_END)):
        result = await email_service.assemble_email_data(db_session)
    assert result == {}


@pytest.mark.asyncio
async def test_assemble_returns_required_keys(db_session, user_alice, week):
    """Email data dict contains persons, leaderboard, and week_label."""
    with ExitStack() as stack:
        for p in _all_ai_patches():
            stack.enter_context(p)
        data = await email_service.assemble_email_data(db_session)

    assert "persons" in data
    assert "leaderboard" in data
    assert "week_label" in data


@pytest.mark.asyncio
async def test_assemble_includes_all_active_users(db_session, user_alice, user_bob, week):
    """All active users appear in persons, even those with zero entries."""
    with ExitStack() as stack:
        for p in _all_ai_patches():
            stack.enter_context(p)
        data = await email_service.assemble_email_data(db_session)

    names = {p["name"] for p in data["persons"]}
    assert "Alice" in names
    assert "Bob" in names


# ---------------------------------------------------------------------------
# assemble_email_data — per-person content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_person_with_entries_gets_ai_content(db_session, user_alice, week):
    """User with entries gets praise, gut_quip, veggie_list, and suggestion."""
    with ExitStack() as stack:
        for p in _all_ai_patches():
            stack.enter_context(p)
        data = await email_service.assemble_email_data(db_session)

    alice = next(p for p in data["persons"] if p["name"] == "Alice")
    assert alice["veggie_count"] == 2
    assert "kale" in alice["veggie_list"]
    assert "blueberry" in alice["veggie_list"]
    assert alice["praise"] == "Great job!"
    assert alice["gut_quip"] == "Gut gold."
    assert alice["suggestion"] == "Try spinach."


@pytest.mark.asyncio
async def test_person_no_entries_gets_encouragement(db_session, user_bob, week):
    """User with no entries gets encouragement praise and empty content fields."""
    with ExitStack() as stack:
        for p in _all_ai_patches():
            stack.enter_context(p)
        data = await email_service.assemble_email_data(db_session)

    bob = next(p for p in data["persons"] if p["name"] == "Bob")
    assert bob["veggie_count"] == 0
    assert bob["veggie_list"] == ""
    assert bob["praise"] == "You got this!"
    assert bob["gut_quip"] == ""
    assert bob["suggestion"] == ""


# ---------------------------------------------------------------------------
# assemble_email_data — leaderboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leaderboard_sorted_descending(db_session, user_alice, user_bob, week):
    """leaderboard is sorted by veggie_count descending with correct ranks."""
    with ExitStack() as stack:
        for p in _all_ai_patches():
            stack.enter_context(p)
        data = await email_service.assemble_email_data(db_session)

    lb = data["leaderboard"]
    counts = [p["veggie_count"] for p in lb]
    assert counts == sorted(counts, reverse=True)
    assert lb[0]["rank"] == 1
    assert lb[0]["name"] == "Alice"   # 2 entries > 0 entries


# ---------------------------------------------------------------------------
# _get_or_cache_spotlight — caching behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_spotlight_cache_miss_calls_ai_and_stores(db_session):
    """On a cache miss, Claude is called and the result is persisted."""
    mock_ai = AsyncMock(return_value={"fun_fact": "Kale is mighty.", "benefit": "Gut hero."})
    with patch(f"{_SVC}.ai_service.generate_veggie_spotlight", new=mock_ai):
        result = await email_service._get_or_cache_spotlight(db_session, "kale")

    mock_ai.assert_called_once_with("kale")
    assert result["fun_fact"] == "Kale is mighty."
    assert result["benefit"] == "Gut hero."


@pytest.mark.asyncio
async def test_spotlight_cache_hit_skips_ai(db_session):
    """On a cache hit, Claude is NOT called and cached values are returned."""
    cached = VeggieBenefitsCache(
        item_name_normalized="spinach",
        fun_fact="Spinach is powerful.",
        benefits_html="Feeds the good bugs.",
    )
    db_session.add(cached)
    await db_session.commit()

    mock_ai = AsyncMock()
    with patch(f"{_SVC}.ai_service.generate_veggie_spotlight", new=mock_ai):
        result = await email_service._get_or_cache_spotlight(db_session, "spinach")

    mock_ai.assert_not_called()
    assert result["fun_fact"] == "Spinach is powerful."
    assert result["benefit"] == "Feeds the good bugs."


# ---------------------------------------------------------------------------
# render_email_html — template rendering
# ---------------------------------------------------------------------------

def test_render_contains_week_label():
    """Rendered HTML includes the week label string."""
    data = {"week_label": "3/8 – 3/14", "persons": [], "leaderboard": []}
    html = email_service.render_email_html(data)
    assert "3/8 – 3/14" in html


def test_render_includes_person_content():
    """Rendered HTML shows each person's name, praise, veggie list, and suggestion."""
    data = {
        "week_label": "3/8 – 3/14",
        "persons": [{
            "name": "Alice",
            "praise": "Phenomenal week!",
            "gut_quip": "Your microbiome is dancing.",
            "veggie_count": 2,
            "veggie_list": "kale, blueberry",
            "picked_veggie": "kale",
            "fun_fact": "Kale has more vitamin C than oranges.",
            "benefit": "Boosts short-chain fatty acids.",
            "suggestion": "Try kimchi next week.",
        }],
        "leaderboard": [{"name": "Alice", "veggie_count": 2, "rank": 1}],
    }
    html = email_service.render_email_html(data)
    assert "Alice" in html
    assert "Phenomenal week!" in html
    assert "kale, blueberry" in html
    assert "Try kimchi next week." in html


def test_render_handles_no_entries_person():
    """Renders cleanly for a person with zero entries (no veggie section shown)."""
    data = {
        "week_label": "3/8 – 3/14",
        "persons": [{
            "name": "Bob",
            "praise": "Come on, you got this!",
            "gut_quip": "",
            "veggie_count": 0,
            "veggie_list": "",
            "picked_veggie": "",
            "fun_fact": "",
            "benefit": "",
            "suggestion": "",
        }],
        "leaderboard": [{"name": "Bob", "veggie_count": 0, "rank": 1}],
    }
    html = email_service.render_email_html(data)
    assert "Bob" in html
    assert "Come on, you got this!" in html
    # Veggie count section should not appear
    assert "plants this week" not in html
