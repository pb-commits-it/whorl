"""NWS + OpenMeteo provider adapters parse real-shape API responses."""

from __future__ import annotations

import httpx
import respx

from whorl.weather.providers import NWSProvider, OpenMeteoProvider


@respx.mock
async def test_nws_provider_parses_periods_to_daily():
    points_url = "https://api.weather.gov/points/38.5266,-97.5777"
    forecast_url = "https://api.weather.gov/gridpoints/TOP/100,100/forecast"
    respx.get(points_url).mock(
        return_value=httpx.Response(200, json={
            "properties": {"forecast": forecast_url},
        })
    )
    respx.get(forecast_url).mock(
        return_value=httpx.Response(200, json={
            "properties": {"periods": [
                {
                    "startTime": "2026-05-29T06:00:00-05:00",
                    "isDaytime": True,
                    "temperature": 87,
                    "windSpeed": "12 mph",
                    "probabilityOfPrecipitation": {"value": 20},
                },
                {
                    "startTime": "2026-05-29T18:00:00-05:00",
                    "isDaytime": False,
                    "temperature": 65,
                    "windSpeed": "6 mph",
                    "probabilityOfPrecipitation": {"value": 10},
                },
                {
                    "startTime": "2026-05-30T06:00:00-05:00",
                    "isDaytime": True,
                    "temperature": 82,
                    "windSpeed": "18 mph",
                    "probabilityOfPrecipitation": {"value": 60},
                },
            ]},
        })
    )

    rows = await NWSProvider().forecast(lat=38.5266, lon=-97.5777, days=7)

    assert len(rows) == 2
    day1 = rows[0]
    assert day1.provider == "NWS"
    assert day1.t_high_f == 87
    assert day1.t_low_f == 65
    assert day1.wind_mph == 12
    # 20% is higher than 10% — max is taken across periods
    assert day1.rain_probability == 0.20

    day2 = rows[1]
    assert day2.t_high_f == 82
    assert day2.wind_mph == 18
    assert day2.rain_probability == 0.60


@respx.mock
async def test_openmeteo_provider_parses_daily_arrays():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json={
            "daily": {
                "time": ["2026-05-29", "2026-05-30", "2026-05-31"],
                "temperature_2m_max": [88.0, 90.0, 84.0],
                "temperature_2m_min": [66.0, 68.0, 62.0],
                "precipitation_sum": [0.0, 0.1, 0.3],
                "precipitation_probability_max": [10, 60, 80],
                "wind_speed_10m_max": [8.0, 14.0, 9.0],
                "wind_gusts_10m_max": [12.0, 22.0, 14.0],
                "relative_humidity_2m_mean": [55.0, 60.0, 70.0],
            },
        })
    )

    rows = await OpenMeteoProvider().forecast(lat=38.5266, lon=-97.5777, days=3)

    assert len(rows) == 3
    r0 = rows[0]
    assert r0.provider == "OpenMeteo"
    assert r0.t_high_f == 88.0
    assert r0.t_low_f == 66.0
    assert r0.rain_in == 0.0
    assert r0.rain_probability == 0.10
    assert r0.wind_mph == 8.0
    assert r0.wind_gust_mph == 12.0
    assert r0.humidity_pct == 55.0


@respx.mock
async def test_openmeteo_provider_handles_empty():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json={"daily": {"time": []}})
    )
    rows = await OpenMeteoProvider().forecast(lat=0, lon=0, days=7)
    assert rows == []
