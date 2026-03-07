"""
Leaderboard router — who's winning this week?
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Entry
from ..schemas import LeaderboardResponse, LeaderboardEntry, WeekResponse
from ..services.auth_service import get_current_user
from ..services.week_service import get_or_create_current_week

router = APIRouter()


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Get the leaderboard for the current week."""
    week = await get_or_create_current_week(db)

    # Get all active users
    users_result = await db.execute(select(User).where(User.is_active == True))
    users = {u.id: u.name for u in users_result.scalars().all()}

    # Count entries per user for this week
    counts_result = await db.execute(
        select(Entry.user_id, func.count(Entry.id).label("cnt"))
        .where(Entry.week_id == week.id)
        .group_by(Entry.user_id)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    # Build standings — include users with 0 entries too
    standings = []
    for user_id, name in users.items():
        standings.append(
            LeaderboardEntry(
                user_id=user_id,
                name=name,
                count=counts.get(user_id, 0),
                rank=0,
            )
        )

    # Sort by count descending, assign ranks
    standings.sort(key=lambda x: x.count, reverse=True)
    for i, s in enumerate(standings):
        s.rank = i + 1

    return LeaderboardResponse(
        week=WeekResponse(
            id=week.id,
            start_date=week.start_date,
            end_date=week.end_date,
            is_active=week.is_active,
        ),
        standings=standings,
    )
