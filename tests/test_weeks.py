"""
Unit tests for week date calculation logic.
Weeks run Sunday–Saturday.
"""
import datetime
import zoneinfo
from unittest.mock import patch
from backend.app.services.week_service import get_current_week_dates


def _make_date(year, month, day):
    return datetime.date(year, month, day)


def test_sunday_is_its_own_week_start():
    # 2024-03-03 is a Sunday
    sunday = _make_date(2024, 3, 3)
    start, end = get_current_week_dates(reference=sunday)
    assert start == sunday
    assert end == _make_date(2024, 3, 9)  # Saturday


def test_saturday_maps_to_its_week_start():
    # 2024-03-09 is a Saturday
    saturday = _make_date(2024, 3, 9)
    start, end = get_current_week_dates(reference=saturday)
    assert start == _make_date(2024, 3, 3)  # Sunday
    assert end == saturday


def test_midweek_maps_to_correct_sunday():
    # 2024-03-06 is a Wednesday
    wednesday = _make_date(2024, 3, 6)
    start, end = get_current_week_dates(reference=wednesday)
    assert start == _make_date(2024, 3, 3)  # Sunday
    assert end == _make_date(2024, 3, 9)    # Saturday


def test_start_is_always_sunday():
    for offset in range(7):
        ref = _make_date(2024, 3, 3) + datetime.timedelta(days=offset)
        start, _ = get_current_week_dates(reference=ref)
        # weekday() == 6 means Sunday
        assert start.weekday() == 6, f"start {start} is not a Sunday (ref={ref})"


def test_end_is_always_saturday():
    for offset in range(7):
        ref = _make_date(2024, 3, 3) + datetime.timedelta(days=offset)
        _, end = get_current_week_dates(reference=ref)
        assert end.weekday() == 5, f"end {end} is not a Saturday (ref={ref})"


def test_week_spans_exactly_7_days():
    ref = _make_date(2024, 6, 15)
    start, end = get_current_week_dates(reference=ref)
    assert (end - start).days == 6


def test_no_args_returns_current_week():
    start, end = get_current_week_dates()
    today = datetime.date.today()
    assert start <= today <= end
    assert start.weekday() == 6
    assert end.weekday() == 5


def test_uses_pacific_time_not_utc():
    """
    Regression test: the server runs in UTC (Fly.io), so at 4 PM Saturday Pacific
    the UTC clock already shows Sunday. Without this fix the week would reset 8 hours
    early. We verify that the function uses Pacific time and returns Saturday's week
    even when UTC has already ticked over to Sunday.

    Simulated moment: Saturday 2026-03-07 11:30 PM Pacific = Sunday 2026-03-08 07:30 AM UTC
    """
    pacific = zoneinfo.ZoneInfo("America/Los_Angeles")
    # Saturday night Pacific — UTC would say it's already Sunday March 8
    saturday_night_pacific = datetime.datetime(2026, 3, 7, 23, 30, 0, tzinfo=pacific)

    with patch("backend.app.services.week_service.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = saturday_night_pacific
        # Restore the non-mocked parts still needed by the function
        mock_dt.date = datetime.date
        mock_dt.timedelta = datetime.timedelta

        start, end = get_current_week_dates()

    # Should still be the week of Mar 1–7, NOT the next week (Mar 8–14)
    assert start == datetime.date(2026, 3, 1), "Week rolled over too early (UTC bug)"
    assert end == datetime.date(2026, 3, 7)
