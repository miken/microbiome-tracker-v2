"""
Pydantic schemas for API validation
"""
import datetime
from typing import Optional
from pydantic import BaseModel


# --- Auth ---
class LoginRequest(BaseModel):
    name: str
    pin: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    name: str


class TokenData(BaseModel):
    user_id: int
    name: str


# --- Entries ---
class EntryCreate(BaseModel):
    item_name: str


class EntryResponse(BaseModel):
    id: int
    item_name: str
    item_name_normalized: str
    created_at: datetime.datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class EntryCreateResponse(BaseModel):
    entry: Optional[EntryResponse] = None
    warnings: list[str] = []
    blocked: bool = False


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    is_near_duplicate: bool
    near_match: Optional[str] = None
    spelling_suggestion: Optional[str] = None


# --- Week ---
class WeekResponse(BaseModel):
    id: int
    start_date: datetime.date
    end_date: datetime.date
    is_active: bool

    class Config:
        from_attributes = True


# --- Leaderboard ---
class LeaderboardEntry(BaseModel):
    user_id: int
    name: str
    count: int
    rank: int


class LeaderboardResponse(BaseModel):
    week: WeekResponse
    standings: list[LeaderboardEntry]


# --- Admin ---
class UserCreate(BaseModel):
    name: str
    pin: str
    gender: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    gender: Optional[str] = None
    email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
