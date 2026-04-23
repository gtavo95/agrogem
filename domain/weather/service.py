from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse


async def fetch_weather(
    provider: WeatherProvider,
    cache: WeatherCache,
    lat: float,
    lon: float,
) -> WeatherResponse:
    cached = await cache.get(lat, lon)
    if cached is not None:
        return cached
    weather = await provider.get_forecast(lat, lon)
    await cache.set(lat, lon, weather)
    return weather
