from dataclasses import dataclass
from statistics import mean

from domain.irrigation_risk.schema import (
    CropName,
    IrrigationRiskFactors,
    IrrigationRiskResponse,
    RiskLevel,
)
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather


@dataclass(frozen=True)
class _CropCoefficients:
    kc: float
    name_es: str


_CROP_KC: dict[CropName, _CropCoefficients] = {
    "corn": _CropCoefficients(kc=1.2, name_es="Maíz"),
    "rice": _CropCoefficients(kc=1.15, name_es="Arroz"),
    "bean": _CropCoefficients(kc=1.1, name_es="Frijol"),
    "wheat": _CropCoefficients(kc=1.1, name_es="Trigo"),
    "coffee": _CropCoefficients(kc=0.9, name_es="Café"),
    "sugarcane": _CropCoefficients(kc=1.2, name_es="Caña de azúcar"),
    "banana": _CropCoefficients(kc=1.1, name_es="Plátano"),
    "tomato": _CropCoefficients(kc=1.05, name_es="Tomate"),
    "potato": _CropCoefficients(kc=1.1, name_es="Papa"),
    "onion": _CropCoefficients(kc=0.95, name_es="Cebolla"),
    "broccoli": _CropCoefficients(kc=1.0, name_es="Brócoli"),
    "rose": _CropCoefficients(kc=1.05, name_es="Rosa"),
}


_LABELS: dict[RiskLevel, str] = {
    "low": "Riego bajo",
    "moderate": "Riego moderado",
    "high": "Riego alto",
    "very_high": "Riego muy alto",
}


def _calc_et0_hargreaves(temp_max: float, temp_min: float, radiation: float) -> float:
    t_mean = (temp_max + temp_min) / 2
    t_range = temp_max - temp_min
    if t_range <= 0:
        t_range = 10.0
    et0 = 0.0023 * (t_mean + 17.8) * (t_range**0.5) * radiation
    return max(et0, 2.0)


def _risk_level(score: float) -> RiskLevel:
    if score < 0.3:
        return "low"
    if score < 0.5:
        return "moderate"
    if score < 0.75:
        return "high"
    return "very_high"


def _aggregate_weather(
    weather: WeatherResponse,
) -> tuple[float, float, float]:
    temp_max = max(
        (t for t in weather.daily.temperature_2m_max if t is not None),
        default=25.0,
    )
    temp_min = min(
        (t for t in weather.daily.temperature_2m_min if t is not None),
        default=15.0,
    )
    radiation = 15.0
    et0_daily = _calc_et0_hargreaves(temp_max, temp_min, radiation)
    et0_total = et0_daily * len(weather.daily.time)

    precip_total = sum(
        p for p in weather.daily.precipitation_sum if p is not None
    )

    return et0_total, precip_total, temp_max


async def compute_irrigation_risk(
    weather_provider: WeatherProvider,
    weather_cache: WeatherCache,
    lat: float,
    lon: float,
    crop: CropName,
) -> IrrigationRiskResponse:
    weather = await fetch_weather(weather_provider, weather_cache, lat, lon)
    et0, precip, temp_max = _aggregate_weather(weather)

    kc = _CROP_KC[crop].kc
    crop_et = et0 * kc

    deficit = max(crop_et - precip, 0.0)
    score = min(deficit / (crop_et + 1.0), 1.0)
    level = _risk_level(score)

    notes = []
    if temp_max > 30:
        notes.append(f"T° máxima alta ({temp_max:.1f}°C) aumenta ET0")
    if deficit > 10:
        notes.append(f"Déficit hídrico de {deficit:.1f} mm")
    if precip < et0 * 0.3:
        notes.append("Precipitación insuficiente para cubrir ET0")

    factors = IrrigationRiskFactors(
        window_days=len(weather.daily.time),
        et0_sum_mm=round(et0, 1),
        precipitation_sum_mm=round(precip, 1),
        crop_water_requirement_mm=round(crop_et, 1),
        soil_water_deficit_mm=round(deficit, 1),
        rule_notes=notes,
    )

    label = _LABELS[level]
    crop_name = _CROP_KC[crop].name_es
    recommendation = max(deficit, 0.0) * 1.1

    return IrrigationRiskResponse(
        crop=crop,
        lat=lat,
        lon=lon,
        risk_score=round(score, 2),
        risk_level=level,
        factors=factors,
        irrigation_recommendation_mm=round(recommendation, 1),
        interpretation=(
            f"{label} para {crop_name}. "
            f"ET0={et0:.1f}mm, precip={precip:.1f}mm, déficit={deficit:.1f}mm. "
            f"Recomendación: aplicar ~{recommendation:.1f}mm."
        ),
    )