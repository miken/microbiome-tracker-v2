"""
Auth router — PIN-based login
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse
from ..services.auth_service import verify_pin, create_token

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with name + PIN, receive a JWT token."""
    result = await db.execute(
        select(User).where(User.name == req.name, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_pin(req.pin, user.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid name or PIN")

    token = create_token(user.id, user.name)
    return LoginResponse(token=token, user_id=user.id, name=user.name)
