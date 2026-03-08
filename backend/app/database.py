"""
Database configuration — async SQLAlchemy with PostgreSQL
Falls back to SQLite for local development
"""
import os
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./microbiome.db"
)

# If using postgres URL from typical providers, fix the scheme
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg doesn't accept query parameters like sslmode/channel_binding — strip them all
# and pass SSL via connect_args instead.
connect_args = {}
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    parsed = urlparse(DATABASE_URL)
    if parsed.query:  # has any query params (sslmode, channel_binding, etc.)
        DATABASE_URL = urlunparse(parsed._replace(query=""))
        connect_args["ssl"] = True

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
