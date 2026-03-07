"""
Weeks router — current and historical week info
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Week
from ..schemas import WeekResponse
from ..services.auth_service import get_current_user
from ..services.week_service import get_or_create_current_week

router = APIRouter()


@router.get("/current", response_model=WeekResponse)
async def get_current_week(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Get the current active week."""
    week = await get_or_create_current_week(db)
    return WeekResponse(
        id=week.id,
        start_date=week.start_date,
        end_date=week.end_date,
        is_active=week.is_active,
    )


@router.get("/history", response_model=list[WeekResponse])
async def list_weeks(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List all weeks, most recent first."""
    result = await db.execute(select(Week).order_by(Week.start_date.desc()).limit(52))
    weeks = result.scalars().all()
    return [
        WeekResponse(id=w.id, start_date=w.start_date, end_date=w.end_date, is_active=w.is_active)
        for w in weeks
    ]
