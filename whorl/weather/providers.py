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
USER_AGENT = "whorl/0.5 (https://github.com/pb-commits-it/whorl)"


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


# ───────────────────────────── Kansas Mesonet ──────────────────────────────────


# Distance band for "use Mesonet as ground truth" — at >25 km the regional
# forecast already captures the field's microclimate better than a far-off
# observation. Documented as a v0.5 design choice in ROADMAP.
MESONET_MAX_KM = 25.0

# Variables we pull. TEMP2MAVG = 2-meter air temperature mean (°C);
# WSPD2MAVG = 2-meter wind average (m/s); WSPD10MMAX = 10-meter wind gust max;
# PRECIP = accumulated precipitation (mm); RELHUM2MAVG = relative humidity (%).
_MESONET_VARS = "TEMP2MAVG,WSPD2MAVG,WSPD10MMAX,PRECIP,RELHUM2MAVG,TEMP2MMAX,TEMP2MMIN"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    R = 6371.0088
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(h))


def nearest_mesonet_station(lat: float, lon: float):
    """Return (station, km) or None when nothing is within MESONET_MAX_KM."""
    from whorl.weather.mesonet_stations import STATIONS

    best = None
    best_km = float("inf")
    for s in STATIONS:
        d = _haversine_km(lat, lon, s.lat, s.lon)
        if d < best_km:
            best, best_km = s, d
    if best is None or best_km > MESONET_MAX_KM:
        return None
    return best, best_km


class MesonetProvider:
    """K-State Mesonet: ground-truth observations from a nearby KS station.

    Unlike NWS/OpenMeteo (forecast), Mesonet reports *measured* conditions over
    the trailing window. We reduce the last 24 hours of hourly observations to
    a single "today" `DailyForecast` row that the recommender treats as the
    most trustworthy data point for *right now*.

    No-op outside Kansas — the caller should consult `nearest_mesonet_station`
    first and not even instantiate this provider if no station is in range.
    """

    name = "Mesonet"
    URL = "https://mesonet.k-state.edu/rest/stationdata/"

    async def forecast(
        self, *, lat: float, lon: float, days: int = 7,
        client: httpx.AsyncClient | None = None,
    ) -> list[DailyForecast]:
        pick = nearest_mesonet_station(lat, lon)
        if pick is None:
            return []
        station, km = pick

        from datetime import UTC, timedelta

        now = datetime.now(UTC).replace(tzinfo=None)
        t_end = now.strftime("%Y%m%d%H%M00")
        t_start = (now - timedelta(hours=24)).strftime("%Y%m%d%H%M00")
        params = {
            "stn": station.name,
            "int": "hour",
            "t_start": t_start,
            "t_end": t_end,
            "vars": _MESONET_VARS,
        }
        async with _client_or(client) as c:
            r = await c.get(self.URL, params=params, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            text = r.text

        if not text or text.startswith("Error"):
            log.warning("mesonet returned non-CSV body: %.80s", text)
            return []

        rows = _parse_mesonet_csv(text)
        if not rows:
            return []

        # Reduce to a single "today" row. Today's high/low from the per-row
        # min/max of TEMP2MAVG (°C → °F); wind from the max of WSPD10MMAX
        # (m/s → mph); rain from the sum of PRECIP (mm → in).
        c_to_f = lambda c: c * 9.0 / 5.0 + 32.0   # noqa: E731
        mps_to_mph = lambda v: v * 2.236936         # noqa: E731
        mm_to_in = lambda v: v / 25.4               # noqa: E731

        temps = [r["TEMP2MAVG"] for r in rows if r.get("TEMP2MAVG") is not None]
        gusts = [r["WSPD10MMAX"] for r in rows if r.get("WSPD10MMAX") is not None]
        winds = [r["WSPD2MAVG"] for r in rows if r.get("WSPD2MAVG") is not None]
        precs = [r["PRECIP"] for r in rows if r.get("PRECIP") is not None]
        hums = [r["RELHUM2MAVG"] for r in rows if r.get("RELHUM2MAVG") is not None]

        return [DailyForecast(
            date=now.date(),
            provider=self.name,
            t_high_f=c_to_f(max(temps)) if temps else None,
            t_low_f=c_to_f(min(temps)) if temps else None,
            rain_in=mm_to_in(sum(precs)) if precs else None,
            rain_probability=None,   # observation, not a forecast
            wind_mph=mps_to_mph(max(winds)) if winds else None,
            wind_gust_mph=mps_to_mph(max(gusts)) if gusts else None,
            humidity_pct=(sum(hums) / len(hums)) if hums else None,
            raw={
                "station": station.name,
                "station_label": station.label,
                "distance_km": round(km, 1),
                "samples": len(rows),
            },
        )]


def _parse_mesonet_csv(text: str) -> list[dict[str, float | None]]:
    """Parse the Mesonet CSV. First line is header; subsequent lines are rows.

    Variable order is *not* guaranteed by the API (per the public docs), so we
    look up by column name.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    header = [h.strip() for h in lines[0].split(",")]
    out: list[dict[str, float | None]] = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(header):
            continue
        row: dict[str, float | None] = {}
        for k, v in zip(header, parts, strict=False):
            if k in ("STATION", "TIMESTAMP"):
                continue
            if v in ("", "None", "NA", "nan"):
                row[k] = None
                continue
            try:
                row[k] = float(v)
            except ValueError:
                row[k] = None
        out.append(row)
    return out


def _client_or(c: httpx.AsyncClient | None):
    """Use the caller's client (so test mocks intercept) or open a fresh one."""
    if c is not None:
        # Wrap in a no-op async context so callsites can use `async with`
        class _Passthrough:
            def __init__(self, inner): self._inner = inner
            async def __aenter__(self): return self._inner
            async def __aexit__(self, *a): return False
        return _Passthrough(c)
    return httpx.AsyncClient(timeout=10.0)


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
