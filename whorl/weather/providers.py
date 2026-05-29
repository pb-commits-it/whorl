"""Provider adapters: NWS (api.weather.gov) + OpenMeteo (api.open-meteo.com).

Both are keyless. NWS gives the canonical US daily forecast; OpenMeteo gives
sub-daily wind + precip-probability detail that we use to pinpoint spray
windows the NWS gridpoint forecast is too coarse for.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

import httpx

log = logging.getLogger("whorl.weather")

# Be explicit about who we are — NWS requires a recognizable User-Agent.
USER_AGENT = "whorl/0.4 (https://github.com/pb-commits-it/whorl)"


@dataclass
class DailyForecast:
    """Normalized one-day forecast for one field from one provider."""

    date: date
    provider: str
    t_high_f: float | None = None
    t_low_f: float | None = None
    rain_in: float | None = None
    rain_probability: float | None = None    # 0..1
    wind_mph: float | None = None
    wind_gust_mph: float | None = None
    humidity_pct: float | None = None
    gdd: float | None = None
    raw: dict = field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
    name: str

    async def forecast(
        self, *, lat: float, lon: float, days: int = 7,
        client: httpx.AsyncClient | None = None,
    ) -> list[DailyForecast]:
        ...


# ───────────────────────────── NWS ─────────────────────────────────────────────


class NWSProvider:
    """National Weather Service: api.weather.gov.

    Two-call flow:
      1. GET /points/{lat},{lon}            → resolves to the local gridpoint
      2. GET /gridpoints/.../forecast       → 7-day high/low/wind/rain narrative
    """

    name = "NWS"
    POINTS = "https://api.weather.gov/points/{lat:.4f},{lon:.4f}"

    async def forecast(
        self, *, lat: float, lon: float, days: int = 7,
        client: httpx.AsyncClient | None = None,
    ) -> list[DailyForecast]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
        own = client is None
        if own:
            client = httpx.AsyncClient(timeout=httpx.Timeout(30.0), headers=headers)
        try:
            pts = await client.get(self.POINTS.format(lat=lat, lon=lon), headers=headers)
            pts.raise_for_status()
            forecast_url = pts.json()["properties"]["forecast"]

            fc = await client.get(forecast_url, headers=headers)
            fc.raise_for_status()
            periods = fc.json()["properties"]["periods"]
        finally:
            if own:
                await client.aclose()

        # NWS periods alternate day/night. Reduce to daily by date.
        by_date: dict[date, dict] = {}
        for p in periods:
            d = datetime.fromisoformat(p["startTime"]).date()
            bucket = by_date.setdefault(
                d, {"high": None, "low": None, "winds": [], "rain_prob": None, "raw": []}
            )
            t = p.get("temperature")
            if p.get("isDaytime") and bucket["high"] is None:
                bucket["high"] = t
            elif not p.get("isDaytime") and bucket["low"] is None:
                bucket["low"] = t

            wind = (p.get("windSpeed") or "").split(" ")[0]
            try:
                bucket["winds"].append(float(wind))
            except (TypeError, ValueError):
                pass

            pop = (p.get("probabilityOfPrecipitation") or {}).get("value")
            if pop is not None:
                cur = bucket["rain_prob"]
                bucket["rain_prob"] = max(cur or 0, pop) / 100.0 if cur is None else max(cur, pop / 100.0)

            bucket["raw"].append(p)

        out: list[DailyForecast] = []
        for d, b in sorted(by_date.items())[:days]:
            out.append(DailyForecast(
                date=d,
                provider=self.name,
                t_high_f=b["high"],
                t_low_f=b["low"],
                wind_mph=max(b["winds"]) if b["winds"] else None,
                rain_probability=b["rain_prob"],
                raw={"periods": b["raw"]},
            ))
        return out


# ───────────────────────────── OpenMeteo ───────────────────────────────────────


class OpenMeteoProvider:
    """OpenMeteo: api.open-meteo.com. No key required.

    For North America we request the NOAA HRRR-backed `gfs_seamless` model; the
    hourly fields are aggregated to daily highs/lows + worst-case wind +
    cumulative rain.
    """

    name = "OpenMeteo"
    URL = "https://api.open-meteo.com/v1/forecast"

    async def forecast(
        self, *, lat: float, lon: float, days: int = 7,
        client: httpx.AsyncClient | None = None,
    ) -> list[DailyForecast]:
        params = {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max,"
                "wind_gusts_10m_max,relative_humidity_2m_mean"
            ),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
            "forecast_days": str(days),
        }
        own = client is None
        if own:
            client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        try:
            r = await client.get(self.URL, params=params, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            data = r.json()
        finally:
            if own:
                await client.aclose()

        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        out: list[DailyForecast] = []
        for i, dstr in enumerate(dates):
            d = date.fromisoformat(dstr)
            out.append(DailyForecast(
                date=d,
                provider=self.name,
                t_high_f=_at(daily, "temperature_2m_max", i),
                t_low_f=_at(daily, "temperature_2m_min", i),
                rain_in=_at(daily, "precipitation_sum", i),
                rain_probability=_pct(_at(daily, "precipitation_probability_max", i)),
                wind_mph=_at(daily, "wind_speed_10m_max", i),
                wind_gust_mph=_at(daily, "wind_gusts_10m_max", i),
                humidity_pct=_at(daily, "relative_humidity_2m_mean", i),
                raw={k: _at(daily, k, i) for k in daily if k != "time"},
            ))
        return out


def _at(d: dict[str, list[Any]], key: str, i: int) -> Any:
    arr = d.get(key)
    if not arr or i >= len(arr):
        return None
    v = arr[i]
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _pct(v: Any) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x / 100.0 if x > 1.0 else x
