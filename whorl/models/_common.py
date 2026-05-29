"""Shared helpers for ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4


def now_utc() -> datetime:
    """Naive UTC. Stays comparable to whatever SQLAlchemy reads back from
    `DateTime` columns on both SQLite and Postgres."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


def new_uuid() -> UUID:
    return uuid4()
