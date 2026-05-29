"""Scouts, photos, identifications."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import new_uuid, now_utc


class Scout(Base):
    __tablename__ = "scouts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    field_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("fields.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(default=now_utc)
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress | complete | failed
    summary: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scout_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("scouts.id"), index=True)
    storage_path: Mapped[str] = mapped_column(Text)
    thumb_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(default=now_utc)


class Identification(Base):
    __tablename__ = "identifications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    photo_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("photos.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)               # 1..N
    taxon_scientific: Mapped[str] = mapped_column(String(200))
    taxon_common: Mapped[Optional[str]] = mapped_column(String(200))
    lifecycle_stage: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    features: Mapped[Optional[list]] = mapped_column(JSON)
    evidence: Mapped[str] = mapped_column(String(20))
    image_quality: Mapped[str] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
