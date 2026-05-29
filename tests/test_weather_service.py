"""Weather caching + spray-window classification."""

from __future__ import annotations

from datetime import date, timedelta


from whorl.models import FieldWeather
from whorl.models._common import now_utc
from whorl.weather.service import _classify, spray_windows


def test_classify_good():
    label, _ = _classify(wind_mph=6, rain_pct=0.05)
    assert label == "good"


def test_classify_marginal_wind():
    label, reason = _classify(wind_mph=12, rain_pct=0.10)
    assert label == "marginal"
    assert "10" in reason or "12" in reason


def test_classify_poor_high_wind():
    label, reason = _classify(wind_mph=18, rain_pct=0.10)
    assert label == "poor"
    assert "drift" in reason


def test_classify_poor_high_rain():
    label, _ = _classify(wind_mph=6, rain_pct=0.70)
    assert label == "poor"


def test_classify_handles_none():
    label, _ = _classify(wind_mph=None, rain_pct=None)
    assert label == "good"


def _row(d: date, *, provider: str, wind: float, rain: float) -> FieldWeather:
    return FieldWeather(
        field_id=None, date=d, provider=provider,
        wind_mph=wind, rain_probability=rain,
        fetched_at=now_utc(),
    )


def test_spray_windows_prefers_openmeteo_over_nws():
    today = now_utc().date()
    rows = [
        _row(today, provider="NWS",       wind=18, rain=0.10),
        _row(today, provider="OpenMeteo", wind=6,  rain=0.05),   # better detail
    ]
    windows = spray_windows(rows)
    assert windows[0].label == "good"
    assert windows[0].wind_mph == 6


def test_spray_windows_filters_past_dates():
    today = now_utc().date()
    past = today - timedelta(days=2)
    rows = [
        _row(past, provider="NWS", wind=6, rain=0.05),
        _row(today, provider="NWS", wind=14, rain=0.30),
    ]
    windows = spray_windows(rows)
    assert len(windows) == 1
    assert windows[0].date == today.isoformat()
