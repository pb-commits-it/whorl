"""Weather + spray-window schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class DailyForecastResponse(BaseModel):
    date: date
    provider: str
    t_high_f: float | None
    t_low_f: float | None
    rain_in: float | None
    rain_probability: float | None
    wind_mph: float | None
    wind_gust_mph: float | None
    humidity_pct: float | None


class SprayWindowResponse(BaseModel):
    date: str
    label: Literal["good", "marginal", "poor"]
    wind_mph: float | None
    rain_probability: float | None
    reason: str


class FieldWeatherResponse(BaseModel):
    field_id: str
    coords: dict
    fetched_at: str | None
    forecasts: list[DailyForecastResponse]
    spray_windows: list[SprayWindowResponse]
