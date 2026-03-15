"""
Admin router — manage users and trigger test emails
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse
from ..services.auth_service import hash_pin, get_current_user
from ..services.email_service import send_weekly_summary

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new participant. No auth required for initial setup — lock this down later."""
    # Check if name already exists
    existing = await db.execute(select(User).where(User.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"User '{req.name}' already exists")

    user = User(
        name=req.name,
        pin_hash=hash_pin(req.pin),
        gender=req.gender,
        email=req.email,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        name=user.name,
        gender=user.gender,
        email=user.email,
        is_active=user.is_active,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List all users."""
    result = await db.execute(select(User).order_by(User.name))
    return [
        UserResponse(id=u.id, name=u.name, gender=u.gender, email=u.email, is_active=u.is_active)
        for u in result.scalars().all()
    ]


@router.post("/send-test-email")
async def trigger_test_email(_=Depends(get_current_user)):
    """Manually trigger the weekly summary email (for testing)."""
    try:
        await send_weekly_summary()
        return {"ok": True, "message": "Email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-previous-week-email")
async def trigger_previous_week_email(_=Depends(get_current_user)):
    """Send the weekly summary for LAST week (e.g. after a missed cron)."""
    try:
        await send_weekly_summary(week_offset=-1)
        return {"ok": True, "message": "Previous week email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
