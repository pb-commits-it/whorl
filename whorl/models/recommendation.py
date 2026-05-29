"""Recommendations — the output of the v0.3 recommender for a scout."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import new_uuid, now_utc


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scout_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("scouts.id"), index=True)

    # Top-level decision
    action: Mapped[str] = mapped_column(String(20))           # no_action|monitor|scout_again|treat
    pest_focus: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[str] = mapped_column(String(10))       # high|medium|low
    plain_english: Mapped[str] = mapped_column(Text)
    threshold_context: Mapped[Optional[str]] = mapped_column(Text)

    # Chemical recommendation (None if action != treat or no rotation available)
    chemical: Mapped[Optional[dict]] = mapped_column(JSON)
    spray_window: Mapped[Optional[dict]] = mapped_column(JSON)

    # Always populated when an alternative exists
    alternatives: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # Provenance
    citations: Mapped[list[dict]] = mapped_column(JSON, default=list)
    model_used: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(20))
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
