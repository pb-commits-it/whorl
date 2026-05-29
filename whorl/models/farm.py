"""Farms and fields.

For an independent farmer, `Organization.type='farmer'` and they have one farm.
For an agronomist, `type='agronomist'` and they have one farm per client.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import new_uuid, now_utc


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    client_name: Mapped[Optional[str]] = mapped_column(String(120))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    farm_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("farms.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    crop: Mapped[str] = mapped_column(String(40))            # corn | soybeans | wheat | sorghum | alfalfa | other
    acres: Mapped[Optional[float]] = mapped_column(Float)
    # v0.4 will swap these for a real geography(polygon); for v0.2 we keep a single centroid.
    centroid_lat: Mapped[Optional[float]] = mapped_column(Float)
    centroid_lon: Mapped[Optional[float]] = mapped_column(Float)
    planting_date: Mapped[Optional[date]] = mapped_column(Date)
    variety: Mapped[Optional[str]] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
