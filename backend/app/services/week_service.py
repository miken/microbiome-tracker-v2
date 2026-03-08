"""
Week management service — handles weekly cycle boundaries
Weeks run Sunday through Saturday, matching the original Google Sheets cadence
"""
import datetime
import zoneinfo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Week

PACIFIC = zoneinfo.ZoneInfo("America/Los_Angeles")


def get_current_week_dates(reference: datetime.date = None) -> tuple[datetime.date, datetime.date]:
    """Get the start (Sunday) and end (Saturday) dates for the current week."""
    if reference is None:
        reference = datetime.datetime.now(PACIFIC).date()
    # Python weekday: Monday=0 ... Sunday=6
    # We want Sunday as start of week
    days_since_sunday = (reference.weekday() + 1) % 7
    start_date = reference - datetime.timedelta(days=days_since_sunday)
    end_date = start_date + datetime.timedelta(days=6)
    return start_date, end_date


async def get_or_create_current_week(db: AsyncSession) -> Week:
    """Get the current week, creating it if it doesn't exist."""
    start_date, end_date = get_current_week_dates()
    
    result = await db.execute(
        select(Week).where(Week.start_date == start_date)
    )
    week = result.scalar_one_or_none()
    
    if not week:
        # Deactivate previous weeks
        prev_result = await db.execute(
            select(Week).where(Week.is_active == True)
        )
        for prev_week in prev_result.scalars().all():
            prev_week.is_active = False

        week = Week(start_date=start_date, end_date=end_date, is_active=True)
        db.add(week)
        try:
            await db.commit()
            await db.refresh(week)
        except IntegrityError:
            # Another concurrent request already created this week — just fetch it
            await db.rollback()
            result = await db.execute(
                select(Week).where(Week.start_date == start_date)
            )
            week = result.scalar_one()

    return week


async def get_week_by_id(db: AsyncSession, week_id: int) -> Week:
    result = await db.execute(select(Week).where(Week.id == week_id))
    return result.scalar_one_or_none()
