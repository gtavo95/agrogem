from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import HTTPError

from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import (
    get_weather_cache,
    get_weather_provider,
    router as weather_router,
)
from domain.weather.schema import WeatherResponse
from tests.conftest import FakeWeatherCache, FakeWeatherProvider, make_weather


def _build_app(
    provider: WeatherProvider,
    cache: WeatherCache,
) -> FastAPI:
    app = FastAPI()
    app.include_router(weather_router)
    app.dependency_overrides[get_weather_provider] = lambda: provider
    app.dependency_overrides[get_weather_cache] = lambda: cache
    return app


def test_weather_endpoint_returns_200_with_payload():
    weather = make_weather()
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    app = _build_app(provider, cache)

    with TestClient(app) as client:
        resp = client.get("/weather", params={"lat": 10.5, "lon": -75.0})

    assert resp.status_code == 200
    body = resp.json()
    assert "current" in body
    assert "hourly" in body
    assert "daily" in body
    assert provider.calls == 1


def test_weather_endpoint_uses_cache_on_second_call():
    weather = make_weather()
    provider = FakeWeatherProvider(response=weather)
    cache = FakeWeatherCache()
    app = _build_app(provider, cache)

    with TestClient(app) as client:
        client.get("/weather", params={"lat": 10.5, "lon": -75.0})
        client.get("/weather", params={"lat": 10.5, "lon": -75.0})

    # Provider called once; second call hit the cache
    assert provider.calls == 1


def test_weather_endpoint_rejects_out_of_range_lat():
    app = _build_app(FakeWeatherProvider(response=make_weather()), FakeWeatherCache())

    with TestClient(app) as client:
        resp = client.get("/weather", params={"lat": 100.0, "lon": 0.0})

    assert resp.status_code == 422


def test_weather_endpoint_rejects_out_of_range_lon():
    app = _build_app(FakeWeatherProvider(response=make_weather()), FakeWeatherCache())

    with TestClient(app) as client:
        resp = client.get("/weather", params={"lat": 0.0, "lon": 200.0})

    assert resp.status_code == 422


def test_weather_endpoint_returns_502_on_provider_error():
    class ExplodingProvider:
        async def get_forecast(self, lat: float, lon: float) -> WeatherResponse:
            raise HTTPError("upstream down")

    app = _build_app(ExplodingProvider(), FakeWeatherCache())

    with TestClient(app) as client:
        resp = client.get("/weather", params={"lat": 0.0, "lon": 0.0})

    assert resp.status_code == 502
    assert "Weather provider error" in resp.json()["detail"]
