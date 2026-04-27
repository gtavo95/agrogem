from __future__ import annotations

from domain.disease_risk.service import (
    _aggregate_weather,
    _risk_level,
    _score_disease,
    compute_disease_risk,
)
from tests.conftest import FakeWeatherCache, FakeWeatherProvider, make_weather


def test_risk_level_buckets():
    assert _risk_level(0.0) == "low"
    assert _risk_level(0.29) == "low"
    assert _risk_level(0.3) == "moderate"
    assert _risk_level(0.49) == "moderate"
    assert _risk_level(0.5) == "high"
    assert _risk_level(0.74) == "high"
    assert _risk_level(0.75) == "very_high"
    assert _risk_level(1.0) == "very_high"


def test_aggregate_weather_ignores_none_values():
    weather = make_weather(
        hourly_temps=[20.0, None, 22.0, None],
        hourly_rh=[70, None, 80, None],
        daily_precip=[0.0, 2.0, 0.5, 3.0, None],
        days=5,
    )
    avg_temp, avg_rh, rainy = _aggregate_weather(weather)
    assert avg_temp == 21.0
    assert avg_rh == 75
    # Only days with precip >= 1.0 count
    assert rainy == 2


def test_aggregate_weather_empty_returns_none():
    weather = make_weather(
        hourly_temps=[None] * 24,
        hourly_rh=[None] * 24,
        daily_precip=[None, None, None, None, None, None, None],
    )
    avg_temp, avg_rh, rainy = _aggregate_weather(weather)
    assert avg_temp is None
    assert avg_rh is None
    assert rainy == 0


def test_score_disease_all_conditions_favorable():
    # coffee_rust: temp 21-25, rh >= 80, rainy >= 3
    score, notes = _score_disease("coffee_rust", avg_temp=23.0, avg_rh=85.0, rainy_days=5)
    assert score == 1.0
    assert len(notes) == 3


def test_score_disease_no_conditions_favorable():
    score, notes = _score_disease("coffee_rust", avg_temp=5.0, avg_rh=40.0, rainy_days=0)
    assert score == 0.0
    assert notes == []


def test_score_disease_partial_conditions():
    # Only temp favorable for coffee_rust
    score, notes = _score_disease("coffee_rust", avg_temp=23.0, avg_rh=40.0, rainy_days=0)
    assert score == 0.4
    assert len(notes) == 1


def test_score_disease_handles_none_inputs():
    score, notes = _score_disease("coffee_rust", avg_temp=None, avg_rh=None, rainy_days=5)
    # Only rainy days count
    assert score == 0.3
    assert len(notes) == 1


async def test_compute_disease_risk_end_to_end_high_risk():
    # Build weather that triggers all three favorable conditions for coffee_rust
    weather = make_weather(
        hourly_temps=[23.0] * (7 * 24),
        hourly_rh=[85] * (7 * 24),
        daily_precip=[2.0, 3.0, 2.0, 0.0, 0.0, 0.0, 0.0],
    )
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()

    result = await compute_disease_risk(provider, cache, lat=0.0, lon=0.0, disease="coffee_rust")

    assert result.disease == "coffee_rust"
    assert result.risk_level == "very_high"
    assert result.risk_score == 1.0
    assert result.factors.rainy_days == 3
    assert provider.calls == 1


async def test_compute_disease_risk_cache_hit_skips_provider():
    weather = make_weather()
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache(store={(0.0, 0.0): weather})

    await compute_disease_risk(provider, cache, lat=0.0, lon=0.0, disease="coffee_rust")

    assert provider.calls == 0


async def test_compute_disease_risk_low_risk_when_conditions_absent():
    # Temps way off, no rain, low humidity
    weather = make_weather(
        hourly_temps=[5.0] * (7 * 24),
        hourly_rh=[30] * (7 * 24),
        daily_precip=[0.0] * 7,
    )
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()

    result = await compute_disease_risk(provider, cache, lat=0.0, lon=0.0, disease="coffee_rust")
    assert result.risk_level == "low"
    assert result.risk_score == 0.0
