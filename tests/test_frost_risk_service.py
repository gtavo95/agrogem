from __future__ import annotations

from domain.frost_risk.service import (
    _aggregate_weather,
    _risk_level,
    compute_frost_risk,
)
from tests.conftest import (
    FakeElevationCache,
    FakeElevationProvider,
    FakeWeatherCache,
    FakeWeatherProvider,
    make_weather,
)


def test_risk_level_thresholds():
    assert _risk_level(0.0) == "low"
    assert _risk_level(0.14) == "low"
    assert _risk_level(0.15) == "moderate"
    assert _risk_level(0.34) == "moderate"
    assert _risk_level(0.35) == "high"
    assert _risk_level(0.59) == "high"
    assert _risk_level(0.6) == "very_high"
    assert _risk_level(1.0) == "very_high"


def test_aggregate_weather_counts_frost_hours():
    temps: list[float | None] = [-2.0, -1.0, 0.5, 5.0, None, -3.0]
    weather = make_weather(hourly_temps=temps + [10.0] * (7 * 24 - len(temps)))
    avg_min, frost_hours = _aggregate_weather(weather)
    assert frost_hours == 3
    assert avg_min is not None


def test_aggregate_weather_none_everywhere():
    weather = make_weather(hourly_temps=[None] * (7 * 24))
    avg_min, frost_hours = _aggregate_weather(weather)
    assert avg_min is None
    assert frost_hours == 0


async def test_compute_frost_risk_no_frost_at_sea_level():
    weather = make_weather(hourly_temps=[18.0] * (7 * 24))
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    elev_provider = FakeElevationProvider(elevation_m=0.0)
    elev_cache = FakeElevationCache()

    result = await compute_frost_risk(
        provider, cache, elev_provider, elev_cache, lat=0.0, lon=0.0
    )

    assert result.risk_level == "low"
    assert result.factors.frost_hours == 0
    # At 0 m elevation the correction is 0
    assert result.factors.altitude_correction_c == 0.0


async def test_compute_frost_risk_altitude_correction_triggers_frost():
    # Forecast shows +3 C at low altitude, but corrected for 4000m it's below 0
    weather = make_weather(hourly_temps=[3.0] * (7 * 24))
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    elev_provider = FakeElevationProvider(elevation_m=4000.0)
    elev_cache = FakeElevationCache()

    result = await compute_frost_risk(
        provider, cache, elev_provider, elev_cache, lat=-13.5, lon=-72.0
    )

    # 4000m * -6.5/1000 = -26.0 C correction -> adjusted min = 3 - 26 = -23
    assert result.factors.altitude_correction_c == -26.0
    assert result.factors.min_temp_c is not None
    assert result.factors.min_temp_c < 0
    assert result.risk_level == "very_high"


async def test_compute_frost_risk_without_elevation_data():
    # Elevation provider returns None — no correction should apply
    weather = make_weather(hourly_temps=[-5.0] * (7 * 24))
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    elev_provider = FakeElevationProvider(elevation_m=None)
    elev_cache = FakeElevationCache()

    result = await compute_frost_risk(
        provider, cache, elev_provider, elev_cache, lat=0.0, lon=0.0
    )

    assert result.elevation_m is None
    assert result.factors.altitude_correction_c == 0.0
    # Temp is already below freezing -> high risk regardless
    assert result.risk_level in ("high", "very_high")


async def test_compute_frost_risk_freezing_probability_computed_under_2c():
    # Adjusted min around 1.0 C -> freezing prob = ((2-1)/2)*100 = 50
    weather = make_weather(hourly_temps=[1.0] * (7 * 24))
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    elev_provider = FakeElevationProvider(elevation_m=0.0)
    elev_cache = FakeElevationCache()

    result = await compute_frost_risk(
        provider, cache, elev_provider, elev_cache, lat=0.0, lon=0.0
    )

    assert result.factors.freezing_probability_pct == 50.0
