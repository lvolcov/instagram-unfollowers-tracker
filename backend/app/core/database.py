"""Async SQLAlchemy engine, session, and DB init."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(
    settings.DB_URL,
    echo=(settings.LOG_LEVEL == "DEBUG"),
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create tables if they don't exist. In production, prefer Alembic migrations."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Import models so SQLAlchemy registers them on Base.metadata.
    # noqa: F401 — imports needed for side effects.
    from backend.app.models import (  # noqa: F401
        account,
        snapshot,
        unfollower,
        whitelist,
        schedule,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
