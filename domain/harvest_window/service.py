from statistics import mean

from domain.harvest_window.schema import (
    CropName,
    HarvestWindowFactors,
    HarvestWindowResponse,
    RiskLevel,
)
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather


_LABELS: dict[RiskLevel, str] = {
    "low": "Ventana no óptima",
    "moderate": "Ventana aceptable",
    "high": "Buena ventana",
    "very_high": "Ventana óptima",
}


def _risk_level(score: float) -> RiskLevel:
    if score < 0.3:
        return "low"
    if score < 0.5:
        return "moderate"
    if score < 0.75:
        return "high"
    return "very_high"


def _calc_window_quality(
    weather: WeatherResponse,
) -> tuple[float | None, float | None, int, int]:
    temp_vals = [t for t in weather.hourly.temperature_2m if t is not None]
    avg_temp = mean(temp_vals) if temp_vals else None

    rh_vals = [r for r in weather.hourly.relative_humidity_2m if r is not None]
    avg_rh = mean(rh_vals) if rh_vals else None

    rainy_days = sum(
        1 for p in weather.daily.precipitation_sum if p is not None and p >= 1.0
    )

    dry_spells = 0
    consecutive_dry = 0
    for p in weather.daily.precipitation_sum:
        if p is None or p < 1.0:
            consecutive_dry += 1
            dry_spells = max(dry_spells, consecutive_dry)
        else:
            consecutive_dry = 0

    return avg_temp, avg_rh, rainy_days, dry_spells


def _evaluate_window(
    crop: CropName,
    avg_temp: float | None,
    avg_rh: float | None,
    rainy_days: int,
    dry_spells: int,
) -> tuple[float, list[str]]:
    score = 0.0
    notes = []

    temp_score = 0.0
    if avg_temp is not None:
        if crop in ("coffee", "tomato", "rose", "strawberry"):
            if 15 <= avg_temp <= 25:
                temp_score = 0.35
                notes.append(f"T° {avg_temp:.1f}°C óptima")
            elif 10 <= avg_temp < 15 or 25 < avg_temp <= 30:
                temp_score = 0.2
                notes.append(f"T° {avg_temp:.1f}°C aceptable")
        elif crop in ("corn", "rice", "bean"):
            if 20 <= avg_temp <= 30:
                temp_score = 0.35
                notes.append(f"T° {avg_temp:.1f}°C óptima")
            elif 15 <= avg_temp < 20 or 30 < avg_temp <= 35:
                temp_score = 0.2

    score += temp_score

    rh_score = 0.0
    if avg_rh is not None:
        if avg_rh < 70:
            rh_score = 0.3
            notes.append(f"HR {avg_rh:.0f}% baja (favorable para secado)")
        elif avg_rh < 80:
            rh_score = 0.15
            notes.append(f"HR {avg_rh:.0f}% moderada")
        else:
            notes.append(f"HR {avg_rh:.0f}% alta (puede dificultar secado)")

    score += rh_score

    rain_penalty = 0.0
    if rainy_days >= 3:
        rain_penalty = 0.3
        notes.append(f"{rainy_days} días de lluvia: posponer cosecha")
    elif rainy_days >= 1:
        rain_penalty = 0.15

    score -= rain_penalty

    if dry_spells >= 3:
        score += 0.25
        notes.append(f"{dry_spells} días secos consecutivos")

    score = max(0.0, min(score, 1.0))

    return score, notes


async def compute_harvest_window(
    weather_provider: WeatherProvider,
    weather_cache: WeatherCache,
    lat: float,
    lon: float,
    crop: CropName,
) -> HarvestWindowResponse:
    weather = await fetch_weather(weather_provider, weather_cache, lat, lon)
    avg_temp, avg_rh, rainy_days, dry_spells = _calc_window_quality(weather)

    score, notes = _evaluate_window(crop, avg_temp, avg_rh, rainy_days, dry_spells)
    level = _risk_level(score)

    dates = []
    warning = None

    if rainy_days >= 3:
        warning = "Lluvias previstas. Esperar ventana seca."
    elif avg_rh is not None and avg_rh > 85:
        warning = "Humedad alta puede afectar calidad de grano/fruto."

    if weather.daily.time:
        window_len = min(3, len(weather.daily.time))
        dates = weather.daily.time[:window_len]

    factors = HarvestWindowFactors(
        window_days=len(weather.daily.time),
        avg_temp_c=avg_temp,
        avg_humidity_pct=avg_rh,
        rainy_days=rainy_days,
        dry_spells=dry_spells,
        rule_notes=notes,
    )

    crop_names_es = {
        "corn": "maíz", "rice": "arroz", "bean": "frijol", "wheat": "trigo",
        "coffee": "café", "sugarcane": "caña", "banana": "plátano",
        "tomato": "tomate", "potato": "papa", "onion": "cebolla",
        "broccoli": "brócoli", "rose": "rosa", "strawberry": "fresa",
    }
    crop_name = crop_names_es.get(crop, crop)
    label = _LABELS[level]

    return HarvestWindowResponse(
        crop=crop,
        lat=lat,
        lon=lon,
        window_score=round(score, 2),
        window_level=level,
        factors=factors,
        optimal_dates=dates,
        warning=warning,
        interpretation=(
            f"{label} para cosecha de {crop_name}. "
            f"T° media: {avg_temp:.1f}°C, HR: {avg_rh:.0f}%. "
            f"Días lluvia: {rainy_days}, días secos: {dry_spells}. "
            f"{f'ADVERTENCIA: {warning}' if warning else ''}"
        ),
    )