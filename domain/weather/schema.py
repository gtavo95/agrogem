from pydantic import BaseModel, ConfigDict


class CurrentWeather(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: str
    temperature_2m: float
    relative_humidity_2m: int
    precipitation: float
    weather_code: int
    wind_speed_10m: float


class HourlyForecast(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: list[str]
    temperature_2m: list[float | None]
    relative_humidity_2m: list[int | None]
    precipitation_probability: list[int | None]


class DailyForecast(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: list[str]
    temperature_2m_max: list[float | None]
    temperature_2m_min: list[float | None]
    precipitation_sum: list[float | None]
    et0_fao_evapotranspiration: list[float | None]
    uv_index_max: list[float | None]


class WeatherResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    timezone: str
    current: CurrentWeather
    hourly: HourlyForecast
    daily: DailyForecast
