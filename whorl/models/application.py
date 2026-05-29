"""Pesticide application history per field.

Drives MOA-rotation enforcement in the v0.3 recommender. Every chemical spray
agronomists log here becomes context the recommender consults when proposing
the next action.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import new_uuid, now_utc


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    field_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("fields.id"), index=True)
    applied_at: Mapped[datetime] = mapped_column()
    pest_target: Mapped[Optional[str]] = mapped_column(String(200))
    product_name: Mapped[str] = mapped_column(String(200))
    active_ingredient: Mapped[Optional[str]] = mapped_column(String(200))
    moa_class: Mapped[Optional[str]] = mapped_column(String(20))   # IRAC | FRAC | HRAC
    moa_group: Mapped[Optional[str]] = mapped_column(String(20))   # e.g. "3A", "5", "28"
    rate: Mapped[Optional[str]] = mapped_column(String(40))
    units: Mapped[Optional[str]] = mapped_column(String(20))
    epa_reg_no: Mapped[Optional[str]] = mapped_column(String(40))
    rei_hours: Mapped[Optional[int]] = mapped_column(Integer)
    phi_days: Mapped[Optional[int]] = mapped_column(Integer)
    outcome: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
