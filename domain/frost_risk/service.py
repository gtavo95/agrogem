from statistics import mean

from domain.elevation.cache import ElevationCache
from domain.elevation.provider import ElevationProvider
from domain.elevation.service import fetch_elevation
from domain.frost_risk.schema import (
    FrostRiskFactors,
    FrostRiskResponse,
    RiskLevel,
)
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather


_LABELS: dict[RiskLevel, str] = {
    "low": "Sin riesgo de helada",
    "moderate": "Riesgo bajo de helada",
    "high": "Riesgo alto de helada",
    "very_high": "Riesgo muy alto de helada",
}


def _risk_level(score: float) -> RiskLevel:
    if score < 0.15:
        return "low"
    if score < 0.35:
        return "moderate"
    if score < 0.6:
        return "high"
    return "very_high"


def _aggregate_weather(weather: WeatherResponse) -> tuple[float | None, int]:
    min_temps = [t for t in weather.hourly.temperature_2m if t is not None]
    avg_min = mean(min_temps) if min_temps else None

    frost_hours = sum(1 for t in min_temps if t is not None and t < 0)

    return avg_min, frost_hours


async def compute_frost_risk(
    weather_provider: WeatherProvider,
    weather_cache: WeatherCache,
    elevation_provider: ElevationProvider,
    elevation_cache: ElevationCache,
    lat: float,
    lon: float,
) -> FrostRiskResponse:
    weather = await fetch_weather(weather_provider, weather_cache, lat, lon)
    avg_min, frost_hours = _aggregate_weather(weather)

    elevation_result = await fetch_elevation(
        elevation_provider, elevation_cache, lat, lon
    )
    elevation = elevation_result.elevation_m if elevation_result else None

    alt_correction = 0.0
    if elevation:
        alt_correction = -(elevation / 1000) * 6.5

    adjusted_min = None
    if avg_min is not None:
        adjusted_min = avg_min + alt_correction

    freezing_prob = 0.0
    if adjusted_min is not None and adjusted_min < 2:
        freezing_prob = ((2 - adjusted_min) / 2) * 100

    score = 0.0
    notes = []

    if frost_hours > 0:
        score = min(frost_hours * 0.15, 0.7)
        notes.append(f"{frost_hours} horas con T° < 0°C")

    if adjusted_min is not None and adjusted_min < 0:
        score = max(score, 0.8)
        notes.append(f"T° mínima ajustada: {adjusted_min:.1f}°C")

    if freezing_prob > 50:
        score = min(score + 0.3, 1.0)
        notes.append(f"Probabilidad de helada: {freezing_prob:.0f}%")

    if adjusted_min is not None and adjusted_min >= 5:
        score = min(score, 0.1)
        notes.append("T° mínima > 5°C sin riesgo")

    if alt_correction < -5:
        notes.append(f"Corrección por elevación: {alt_correction:.1f}°C ({(abs(alt_correction)/6.5)*1000:.0f}m)")

    level = _risk_level(score)

    factors = FrostRiskFactors(
        window_days=len(weather.daily.time),
        min_temp_c=adjusted_min,
        frost_hours=frost_hours,
        freezing_probability_pct=round(freezing_prob, 1),
        altitude_correction_c=round(alt_correction, 1),
        rule_notes=notes,
    )

    label = _LABELS[level]
    location = f"({lat:.2f}, {lon:.2f})"
    elev_info = f", elevación {elevation:.0f}m" if elevation else ""

    return FrostRiskResponse(
        lat=lat,
        lon=lon,
        elevation_m=elevation,
        risk_score=round(score, 2),
        risk_level=level,
        factors=factors,
        interpretation=(
            f"{label} para {location}{elev_info}. "
            f"T° mín ajustada: {adjusted_min:.1f}°C (corregida {alt_correction:.1f}°C por elev). "
            f"{frost_hours} horas bajo 0°C. Prob helada: {freezing_prob:.0f}%."
        ),
    )