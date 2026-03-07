"""
Authentication service — PIN-based auth with JWT tokens
"""
import os
import hashlib
import hmac
import jwt
import datetime
from typing import Optional
from fastapi import HTTPException, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from ..schemas import TokenData

SECRET_KEY = os.environ.get("SECRET_KEY", "microbiome-tracker-dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 90  # Long-lived for convenience — it's a family app


def hash_pin(pin: str) -> str:
    """Hash a PIN using SHA-256 with a salt."""
    salt = os.environ.get("PIN_SALT", "microbiome-salt")
    return hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify a PIN against its hash."""
    return hmac.compare_digest(hash_pin(pin), pin_hash)


def create_token(user_id: int, name: str) -> str:
    """Create a JWT token for the user."""
    payload = {
        "user_id": user_id,
        "name": name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(user_id=payload["user_id"], name=payload["name"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate the current user from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ", 1)[1]
    token_data = decode_token(token)
    
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user
