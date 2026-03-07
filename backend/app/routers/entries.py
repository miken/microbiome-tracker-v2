"""
Entries router — CRUD for veggie/fruit/nut/spice entries
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Entry
from ..schemas import EntryCreate, EntryCreateResponse, EntryResponse, DuplicateCheckResponse
from ..services.auth_service import get_current_user
from ..services.week_service import get_or_create_current_week
from ..services.item_service import normalize_item, check_spelling, find_near_duplicate

router = APIRouter()


async def _get_user_entries_for_week(db: AsyncSession, user_id: int, week_id: int) -> list[Entry]:
    result = await db.execute(
        select(Entry)
        .where(Entry.user_id == user_id, Entry.week_id == week_id)
        .order_by(Entry.created_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=EntryCreateResponse)
async def add_entry(
    req: EntryCreate,
    force: bool = Query(False, description="Force add even with warnings"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new veggie/fruit/nut/spice entry for the current week."""
    item_name = req.item_name.strip()
    if not item_name:
        raise HTTPException(status_code=400, detail="Item name cannot be empty")

    normalized = normalize_item(item_name)
    week = await get_or_create_current_week(db)

    # Get existing entries for duplicate checking
    existing = await _get_user_entries_for_week(db, current_user.id, week.id)
    existing_normalized = [e.item_name_normalized for e in existing]

    warnings = []

    # 1. Exact duplicate check
    if normalized in existing_normalized:
        return EntryCreateResponse(
            entry=None,
            warnings=[f"You already logged '{normalized}' this week!"],
            blocked=True,
        )

    # 2. Near-duplicate check
    near = find_near_duplicate(normalized, existing_normalized)
    if near and not force:
        return EntryCreateResponse(
            entry=None,
            warnings=[f"This looks similar to '{near}' which you already logged. Add ?force=true to add anyway."],
            blocked=True,
        )
    elif near:
        warnings.append(f"Note: similar to '{near}' already logged.")

    # 3. Spelling suggestion
    suggestion = check_spelling(item_name)
    if suggestion and suggestion != normalized:
        warnings.append(f"Did you mean '{suggestion}'?")

    # Create the entry
    entry = Entry(
        user_id=current_user.id,
        week_id=week.id,
        item_name=item_name,
        item_name_normalized=normalized,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return EntryCreateResponse(
        entry=EntryResponse(
            id=entry.id,
            item_name=entry.item_name,
            item_name_normalized=entry.item_name_normalized,
            created_at=entry.created_at,
        ),
        warnings=warnings,
        blocked=False,
    )


@router.get("", response_model=list[EntryResponse])
async def list_my_entries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all my entries for the current week."""
    week = await get_or_create_current_week(db)
    entries = await _get_user_entries_for_week(db, current_user.id, week.id)
    return [
        EntryResponse(
            id=e.id,
            item_name=e.item_name,
            item_name_normalized=e.item_name_normalized,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.get("/user/{user_id}", response_model=list[EntryResponse])
async def list_user_entries(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View another user's entries for the current week."""
    week = await get_or_create_current_week(db)
    entries = await _get_user_entries_for_week(db, user_id, week.id)

    # Get the user's name
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    user_name = user.name if user else "Unknown"

    return [
        EntryResponse(
            id=e.id,
            item_name=e.item_name,
            item_name_normalized=e.item_name_normalized,
            created_at=e.created_at,
            user_name=user_name,
        )
        for e in entries
    ]


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of your own entries."""
    result = await db.execute(
        select(Entry).where(Entry.id == entry_id, Entry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found or not yours")

    await db.delete(entry)
    await db.commit()
    return {"ok": True}


@router.get("/check", response_model=DuplicateCheckResponse)
async def check_entry(
    item_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pre-check an item for duplicates and spelling before adding."""
    normalized = normalize_item(item_name)
    week = await get_or_create_current_week(db)
    existing = await _get_user_entries_for_week(db, current_user.id, week.id)
    existing_normalized = [e.item_name_normalized for e in existing]

    is_dup = normalized in existing_normalized
    near = find_near_duplicate(normalized, existing_normalized) if not is_dup else None
    spelling = check_spelling(item_name)

    return DuplicateCheckResponse(
        is_duplicate=is_dup,
        is_near_duplicate=near is not None,
        near_match=near,
        spelling_suggestion=spelling if spelling and spelling != normalized else None,
    )
