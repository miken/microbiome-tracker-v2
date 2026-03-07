"""
Shared test fixtures.

Uses an in-memory SQLite database with StaticPool so that all async sessions
(test session + request handler sessions) share the same underlying connection.
"""
import os

# Must be set before any app imports so module-level constants pick them up.
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["PIN_SALT"] = "test-salt"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models import User
from backend.app.services.auth_service import hash_pin, create_token

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provides a DB session and overrides the app's get_db dependency."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        yield session

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTP test client wired to the test database."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def user(db_session):
    u = User(name="TestUser", pin_hash=hash_pin("1234"))
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def second_user(db_session):
    u = User(name="OtherUser", pin_hash=hash_pin("5678"))
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def auth_headers(user):
    token = create_token(user.id, user.name)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(second_user):
    token = create_token(second_user.id, second_user.name)
    return {"Authorization": f"Bearer {token}"}
