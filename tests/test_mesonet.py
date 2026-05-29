"""Mesonet provider: CSV parsing, distance gate, today-prefer routing."""

from __future__ import annotations

from datetime import timedelta

import respx

from whorl.models import FieldWeather
from whorl.models._common import now_utc
from whorl.weather.providers import (
    MesonetProvider,
    _haversine_km,
    nearest_mesonet_station,
)
from whorl.weather.service import spray_windows


def test_haversine_known_distance():
    # Manhattan KS → Topeka KS ≈ 85 km
    km = _haversine_km(39.2050, -96.5847, 39.0473, -95.6890)
    assert 70 < km < 100


def test_nearest_mesonet_in_kansas_within_radius():
    # A field 8 km west of Manhattan station
    res = nearest_mesonet_station(39.2050, -96.6750)
    assert res is not None
    station, km = res
    assert station.name == "Manhattan"
    assert km < 25


def test_nearest_mesonet_far_outside_kansas_returns_none():
    # New York City — way outside Kansas
    assert nearest_mesonet_station(40.7128, -74.0060) is None


@respx.mock
async def test_mesonet_provider_parses_csv_and_reduces_to_today():
    csv = (
        "TIMESTAMP,STATION,TEMP2MAVG,WSPD2MAVG,WSPD10MMAX,PRECIP,RELHUM2MAVG\n"
        "2026-05-29 06:00:00,Manhattan,15.0,2.0,4.0,0.0,80\n"
        "2026-05-29 09:00:00,Manhattan,20.0,3.0,7.5,0.0,70\n"
        "2026-05-29 12:00:00,Manhattan,28.0,5.0,12.0,0.5,55\n"
        "2026-05-29 15:00:00,Manhattan,30.0,6.0,15.0,0.0,50\n"
    )
    respx.get("https://mesonet.k-state.edu/rest/stationdata/").respond(200, text=csv)

    # Coordinates near Manhattan, KS
    rows = await MesonetProvider().forecast(lat=39.2050, lon=-96.5847, days=1)
    assert len(rows) == 1
    r = rows[0]
    assert r.provider == "Mesonet"
    # 15 °C → 59 °F low; 30 °C → 86 °F high
    assert r.t_low_f is not None and 58 < r.t_low_f < 60
    assert r.t_high_f is not None and 85 < r.t_high_f < 87
    # Wind gust max: 15 m/s → ~33.5 mph
    assert r.wind_gust_mph is not None and 33 < r.wind_gust_mph < 34
    # Wind avg max: 6 m/s → ~13.4 mph
    assert r.wind_mph is not None and 13 < r.wind_mph < 14
    # Precip sum: 0.5 mm → ~0.0197 in
    assert r.rain_in is not None and 0.015 < r.rain_in < 0.025
    # Humidity mean: (80+70+55+50)/4 = 63.75
    assert r.humidity_pct is not None and 63 < r.humidity_pct < 64
    assert r.raw["station"] == "Manhattan"
    assert r.raw["samples"] == 4


@respx.mock
async def test_mesonet_provider_returns_empty_outside_kansas():
    # Should not even hit the API — short-circuits on distance
    rows = await MesonetProvider().forecast(lat=40.7128, lon=-74.0060, days=1)
    assert rows == []


@respx.mock
async def test_mesonet_provider_handles_api_error_body():
    respx.get("https://mesonet.k-state.edu/rest/stationdata/").respond(
        200, text="Error: 'TAIR' is not a valid variable name",
    )
    rows = await MesonetProvider().forecast(lat=39.2050, lon=-96.5847, days=1)
    assert rows == []


def _row(d, *, provider, wind=None, rain_pct=None, raw=None):
    return FieldWeather(
        field_id=None, date=d, provider=provider,
        wind_mph=wind, rain_probability=rain_pct,
        raw=raw, fetched_at=now_utc(),
    )


def test_spray_windows_prefers_mesonet_for_today():
    today = now_utc().date()
    rows = [
        _row(today, provider="OpenMeteo", wind=18, rain_pct=0.05),
        _row(today, provider="Mesonet",   wind=4,  rain_pct=None,
             raw={"station_label": "Manhattan"}),
    ]
    windows = spray_windows(rows)
    assert len(windows) == 1
    w = windows[0]
    # Mesonet wins for wind today; rain falls back to OpenMeteo (0.05, fine).
    assert w.label == "good"
    assert w.wind_mph == 4
    assert "Manhattan obs" in w.reason


def test_spray_windows_ignores_mesonet_for_future_dates():
    today = now_utc().date()
    tomorrow = today + timedelta(days=1)
    rows = [
        # Mesonet only carries today, but defensively check it doesn't leak
        _row(tomorrow, provider="Mesonet",   wind=2,  rain_pct=None,
             raw={"station_label": "Manhattan"}),
        _row(tomorrow, provider="OpenMeteo", wind=18, rain_pct=0.40),
    ]
    windows = spray_windows(rows)
    tomorrow_w = next(w for w in windows if w.date == tomorrow.isoformat())
    # OpenMeteo wins for the future date — 18 mph → poor
    assert tomorrow_w.label == "poor"
    assert tomorrow_w.wind_mph == 18
