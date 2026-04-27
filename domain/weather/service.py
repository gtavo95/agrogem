from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse


def _avg(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else None


def _sum(values: list[float | None]) -> float:
    return sum(v for v in values if v is not None)


def _interpret(w: WeatherResponse) -> str:
    cur = w.current
    daily = w.daily
    parts = [
        f"Clima actual: {cur.temperature_2m:.1f}°C, "
        f"{cur.relative_humidity_2m}% humedad, "
        f"viento {cur.wind_speed_10m:.1f} km/h."
    ]
    tmax = _avg(daily.temperature_2m_max)
    tmin = _avg(daily.temperature_2m_min)
    p = _sum(daily.precipitation_sum)
    et = _sum(daily.et0_fao_evapotranspiration)
    if tmax is not None and tmin is not None:
        parts.append(
            f"Próximos 7 días: max {tmax:.1f}°C / min {tmin:.1f}°C, "
            f"lluvia acumulada {p:.1f} mm, ET₀ {et:.1f} mm."
        )
    return " ".join(parts)


async def fetch_weather(
    provider: WeatherProvider,
    cache: WeatherCache,
    lat: float,
    lon: float,
) -> WeatherResponse:
    cached = await cache.get(lat, lon)
    if cached is not None:
        cached.interpretation = _interpret(cached)
        return cached
    weather = await provider.get_forecast(lat, lon)
    weather.interpretation = _interpret(weather)
    await cache.set(lat, lon, weather)
    return weather
