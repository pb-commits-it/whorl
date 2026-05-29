"""Database engine, async session factory, and the SQLAlchemy `Base`."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> AsyncEngine:
    # `pool_pre_ping` survives idle disconnects on a long-running uvicorn.
    return create_async_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables (idempotent). Used in dev + tests; Alembic takes over in v0.3."""
    # Import models so they register with `Base.metadata`.
    from whorl import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, rolls back on exception, lets the caller commit."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
