"""Per-field daily weather rows — cached forecasts that feed the recommender."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from whorl.db import Base
from whorl.models._common import now_utc


class FieldWeather(Base):
    """One day's forecast for one field from one provider.

    Multiple provider rows per (field, date) are allowed (NWS + OpenMeteo can
    coexist for the same date and the recommender uses whichever is best for
    that signal).
    """

    __tablename__ = "field_weather"
    __table_args__ = (
        UniqueConstraint("field_id", "date", "provider", name="uq_field_weather_fdp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("fields.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(20))     # 'NWS' | 'OpenMeteo' | 'KansasMesonet'

    t_high_f: Mapped[Optional[float]] = mapped_column(Float)
    t_low_f: Mapped[Optional[float]] = mapped_column(Float)
    rain_in: Mapped[Optional[float]] = mapped_column(Float)
    rain_probability: Mapped[Optional[float]] = mapped_column(Float)   # 0..1
    wind_mph: Mapped[Optional[float]] = mapped_column(Float)
    wind_gust_mph: Mapped[Optional[float]] = mapped_column(Float)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float)
    gdd: Mapped[Optional[float]] = mapped_column(Float)

    raw: Mapped[Optional[dict]] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(default=now_utc)
