from dataclasses import dataclass
from statistics import mean

from domain.disease_risk.schema import (
    DiseaseName,
    DiseaseRiskFactors,
    DiseaseRiskResponse,
    RiskLevel,
)
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather


@dataclass(frozen=True)
class _DiseaseRule:
    temp_range: tuple[float, float]
    rh_threshold: float
    rainy_days_threshold: int
    name_es: str


_DISEASE_RULES: dict[DiseaseName, _DiseaseRule] = {
    "coffee_rust": _DiseaseRule(
        temp_range=(21.0, 25.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="roya del café (Hemileia vastatrix)",
    ),
    "late_blight": _DiseaseRule(
        temp_range=(10.0, 25.0),
        rh_threshold=85.0,
        rainy_days_threshold=4,
        name_es="tizón tardío (Phytophthora infestans)",
    ),
    "corn_rust": _DiseaseRule(
        temp_range=(20.0, 26.0),
        rh_threshold=75.0,
        rainy_days_threshold=3,
        name_es="roya del maíz (Puccinia sorghi)",
    ),
}


_RISK_LABELS: dict[RiskLevel, str] = {
    "low": "Riesgo bajo",
    "moderate": "Riesgo moderado",
    "high": "Riesgo alto",
    "very_high": "Riesgo muy alto",
}


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
) -> tuple[float | None, float | None, int]:
    hourly_temp = [t for t in weather.hourly.temperature_2m if t is not None]
    hourly_rh = [r for r in weather.hourly.relative_humidity_2m if r is not None]
    avg_temp = mean(hourly_temp) if hourly_temp else None
    avg_rh = mean(hourly_rh) if hourly_rh else None
    rainy_days = sum(
        1 for p in weather.daily.precipitation_sum if p is not None and p >= 1.0
    )
    return avg_temp, avg_rh, rainy_days


def _score_disease(
    disease: DiseaseName,
    avg_temp: float | None,
    avg_rh: float | None,
    rainy_days: int,
) -> tuple[float, list[str]]:
    rule = _DISEASE_RULES[disease]
    t_lo, t_hi = rule.temp_range
    score = 0.0
    notes: list[str] = []
    if avg_temp is not None and t_lo <= avg_temp <= t_hi:
        score += 0.4
        notes.append(
            f"T° media {avg_temp:.1f}°C en rango óptimo [{t_lo:.0f}-{t_hi:.0f}°C]"
        )
    if avg_rh is not None and avg_rh >= rule.rh_threshold:
        score += 0.3
        notes.append(
            f"humedad relativa {avg_rh:.0f}% ≥ {rule.rh_threshold:.0f}%"
        )
    if rainy_days >= rule.rainy_days_threshold:
        score += 0.3
        notes.append(
            f"{rainy_days} días lluviosos (umbral {rule.rainy_days_threshold})"
        )
    return score, notes


def _interpret(
    disease: DiseaseName, level: RiskLevel, factors: DiseaseRiskFactors
) -> str:
    name_es = _DISEASE_RULES[disease].name_es
    label = _RISK_LABELS[level]
    reasons = (
        "; ".join(factors.rule_notes)
        if factors.rule_notes
        else "ninguna condición favorable detectada"
    )
    return (
        f"{label} de {name_es} en los próximos {factors.window_days} días. "
        f"Factores: {reasons}."
    )


async def compute_disease_risk(
    weather_provider: WeatherProvider,
    weather_cache: WeatherCache,
    lat: float,
    lon: float,
    disease: DiseaseName,
) -> DiseaseRiskResponse:
    weather = await fetch_weather(weather_provider, weather_cache, lat, lon)
    avg_temp, avg_rh, rainy_days = _aggregate_weather(weather)
    score, notes = _score_disease(disease, avg_temp, avg_rh, rainy_days)
    level = _risk_level(score)
    factors = DiseaseRiskFactors(
        window_days=len(weather.daily.time),
        avg_temp_c=avg_temp,
        avg_humidity_pct=avg_rh,
        rainy_days=rainy_days,
        rule_notes=notes,
    )
    return DiseaseRiskResponse(
        disease=disease,
        lat=lat,
        lon=lon,
        risk_score=round(score, 2),
        risk_level=level,
        factors=factors,
        interpretation=_interpret(disease, level, factors),
    )
