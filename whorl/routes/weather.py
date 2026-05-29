"""Weather routes — cached + on-demand-refreshable forecasts per field."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, FieldWeather, User
from whorl.schemas.weather import (
    DailyForecastResponse,
    FieldWeatherResponse,
    SprayWindowResponse,
)
from whorl.weather.service import (
    DEFAULT_LAT,
    DEFAULT_LON,
    forecast_for_field,
    spray_windows,
)

router = APIRouter()


async def _field_in_org(
    session: AsyncSession, field_id: UUID, org_id: UUID,
) -> Field | None:
    return (await session.execute(
        select(Field).join(Farm, Field.farm_id == Farm.id)
        .where(Field.id == field_id, Farm.org_id == org_id)
    )).scalar_one_or_none()


def _row_to_response(r: FieldWeather) -> DailyForecastResponse:
    return DailyForecastResponse(
        date=r.date,
        provider=r.provider,
        t_high_f=r.t_high_f,
        t_low_f=r.t_low_f,
        rain_in=r.rain_in,
        rain_probability=r.rain_probability,
        wind_mph=r.wind_mph,
        wind_gust_mph=r.wind_gust_mph,
        humidity_pct=r.humidity_pct,
    )


@router.get(
    "/api/fields/{field_id}/weather",
    response_model=FieldWeatherResponse,
)
async def get_field_weather(
    field_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh: Annotated[bool, Query(description="Force re-fetch even if cache is fresh")] = False,
    days: Annotated[int, Query(ge=1, le=14)] = 7,
) -> FieldWeatherResponse:
    field = await _field_in_org(session, field_id, user.org_id)
    if field is None:
        raise HTTPException(status_code=404, detail="field not found")

    rows = await forecast_for_field(session, field, days=days, force=refresh)
    fetched = max((r.fetched_at for r in rows), default=None) if rows else None
    return FieldWeatherResponse(
        field_id=str(field.id),
        coords={
            "lat": field.centroid_lat or DEFAULT_LAT,
            "lon": field.centroid_lon or DEFAULT_LON,
            "is_default": field.centroid_lat is None or field.centroid_lon is None,
        },
        fetched_at=fetched.isoformat() if fetched else None,
        forecasts=[_row_to_response(r) for r in rows],
        spray_windows=[
            SprayWindowResponse(
                date=w.date, label=w.label,
                wind_mph=w.wind_mph, rain_probability=w.rain_probability,
                reason=w.reason,
            ) for w in spray_windows(rows, days=days)
        ],
    )
