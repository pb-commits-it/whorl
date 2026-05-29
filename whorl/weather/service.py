"""Weather caching service + spray-window analysis.

Routing rule (v0.4):
- All US: NWS for canonical daily highs/lows
- Everywhere: OpenMeteo for finer wind + sub-daily precip-probability detail
- v0.5: add Kansas Mesonet as primary obs source within 25 km of a KS station.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.models import Field, FieldWeather
from whorl.models._common import now_utc
from whorl.weather.providers import (
    DailyForecast,
    NWSProvider,
    OpenMeteoProvider,
)

if TYPE_CHECKING:
    pass

# Used when a Field has no GPS centroid recorded yet — central Kansas, so the
# corn-earworm demo still pulls real KS weather without manual coord entry.
DEFAULT_LAT = 38.5266
DEFAULT_LON = -97.5777

# Re-fetch this often. NWS / OpenMeteo update much more frequently than this,
# but for daily-resolution forecasts a six-hour staleness is fine and keeps the
# external call rate sane.
CACHE_TTL = timedelta(hours=6)


@dataclass
class SprayWindow:
    """One day's spray-window classification, what the recommender consumes."""

    date: str          # YYYY-MM-DD
    label: str         # 'good' | 'marginal' | 'poor'
    wind_mph: float | None
    rain_probability: float | None
    reason: str


def _is_cache_fresh(row: FieldWeather) -> bool:
    if row.fetched_at is None:
        return False
    return (now_utc() - row.fetched_at) < CACHE_TTL


async def _store_forecast(
    session: AsyncSession, *, field_id: UUID, forecasts: list[DailyForecast],
) -> None:
    """Upsert per (field, date, provider)."""
    for fc in forecasts:
        existing = (await session.execute(
            select(FieldWeather).where(
                FieldWeather.field_id == field_id,
                FieldWeather.date == fc.date,
                FieldWeather.provider == fc.provider,
            )
        )).scalar_one_or_none()
        if existing is None:
            session.add(FieldWeather(
                field_id=field_id,
                date=fc.date,
                provider=fc.provider,
                t_high_f=fc.t_high_f,
                t_low_f=fc.t_low_f,
                rain_in=fc.rain_in,
                rain_probability=fc.rain_probability,
                wind_mph=fc.wind_mph,
                wind_gust_mph=fc.wind_gust_mph,
                humidity_pct=fc.humidity_pct,
                gdd=fc.gdd,
                raw=fc.raw,
                fetched_at=now_utc(),
            ))
        else:
            for col in (
                "t_high_f", "t_low_f", "rain_in", "rain_probability",
                "wind_mph", "wind_gust_mph", "humidity_pct", "gdd", "raw",
            ):
                setattr(existing, col, getattr(fc, col))
            existing.fetched_at = now_utc()


async def fetch_and_cache(
    session: AsyncSession,
    field: Field,
    *,
    force: bool = False,
    days: int = 7,
) -> list[FieldWeather]:
    """Return cached field_weather rows, fetching fresh forecasts if stale."""
    rows = (await session.execute(
        select(FieldWeather).where(FieldWeather.field_id == field.id)
        .order_by(FieldWeather.date)
    )).scalars().all()

    if not force and rows and all(_is_cache_fresh(r) for r in rows[:days]):
        return rows

    lat = field.centroid_lat or DEFAULT_LAT
    lon = field.centroid_lon or DEFAULT_LON

    providers = [NWSProvider(), OpenMeteoProvider()]
    new_forecasts: list[DailyForecast] = []
    for p in providers:
        try:
            new_forecasts.extend(await p.forecast(lat=lat, lon=lon, days=days))
        except Exception as exc:   # noqa: BLE001 — partial-success is fine
            import logging
            logging.getLogger("whorl.weather").warning(
                "provider %s failed for field %s: %s", p.name, field.id, exc,
            )

    await _store_forecast(session, field_id=field.id, forecasts=new_forecasts)
    await session.commit()

    return (await session.execute(
        select(FieldWeather).where(FieldWeather.field_id == field.id)
        .order_by(FieldWeather.date, FieldWeather.provider)
    )).scalars().all()


async def forecast_for_field(
    session: AsyncSession, field: Field, *, days: int = 7, force: bool = False,
) -> list[FieldWeather]:
    """Cached + freshly-fetched-if-stale forecast for a field."""
    return await fetch_and_cache(session, field, force=force, days=days)


def _classify(wind_mph: float | None, rain_pct: float | None) -> tuple[str, str]:
    """Return (label, reason). Thresholds match standard ag spray guidance."""
    parts: list[str] = []
    label = "good"
    if wind_mph is not None and wind_mph >= 15:
        label = "poor"
        parts.append(f"winds {wind_mph:.0f} mph (≥15 — drift risk)")
    elif wind_mph is not None and wind_mph >= 10:
        if label == "good":
            label = "marginal"
        parts.append(f"winds {wind_mph:.0f} mph (≥10 — marginal)")

    if rain_pct is not None and rain_pct >= 0.50:
        label = "poor"
        parts.append(f"rain {int(rain_pct * 100)}% (washoff risk)")
    elif rain_pct is not None and rain_pct >= 0.30:
        if label == "good":
            label = "marginal"
        parts.append(f"rain {int(rain_pct * 100)}%")

    if not parts:
        wind_str = f"winds {wind_mph:.0f} mph" if wind_mph is not None else "winds low"
        rain_str = (
            f"rain {int(rain_pct * 100)}%" if rain_pct is not None else "rain low"
        )
        parts = [wind_str, rain_str]
    return label, ", ".join(parts)


def spray_windows(rows: list[FieldWeather], *, days: int = 7) -> list[SprayWindow]:
    """Reduce stored rows → one classification per upcoming date.

    For each date, prefer OpenMeteo's wind + rain_probability when present
    (sub-daily detail, better calibrated for short windows); fall back to NWS.
    """
    today = now_utc().date()
    by_date_provider: dict[tuple, FieldWeather] = {(r.date, r.provider): r for r in rows}
    dates = sorted({r.date for r in rows if r.date >= today})[:days]

    windows: list[SprayWindow] = []
    for d in dates:
        om = by_date_provider.get((d, "OpenMeteo"))
        nws = by_date_provider.get((d, "NWS"))
        wind = (om.wind_mph if om and om.wind_mph is not None else
                nws.wind_mph if nws else None)
        rain = (om.rain_probability if om and om.rain_probability is not None else
                nws.rain_probability if nws else None)
        label, reason = _classify(wind, rain)
        windows.append(SprayWindow(
            date=d.isoformat(),
            label=label,
            wind_mph=wind,
            rain_probability=rain,
            reason=reason,
        ))
    return windows
