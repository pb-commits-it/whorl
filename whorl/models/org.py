"""Organizations, users, magic-link auth tokens."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import new_uuid, now_utc


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20))           # 'farmer' | 'agronomist'
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="owner")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    last_login_at: Mapped[Optional[datetime]] = mapped_column()


class AuthToken(Base):
    """Single-use magic-link token. Stored as random URL-safe string."""

    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[Optional[datetime]] = mapped_column()
