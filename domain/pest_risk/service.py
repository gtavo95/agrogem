from dataclasses import dataclass
from datetime import datetime
from statistics import mean

from domain.pest_risk.schema import (
    HumidityLogic,
    LifeStageRisk,
    PestName,
    PestRiskFactors,
    PestRiskResponse,
    PestType,
    RiskLevel,
)
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather


@dataclass(frozen=True)
class _PestRule:
    temp_range: tuple[float, float]
    humidity_min: float | None
    humidity_max: float | None
    humidity_logic: HumidityLogic
    pest_type: PestType
    life_stage_risk: LifeStageRisk
    affected_crops: tuple[str, ...]
    name_es: str
    scientific_name: str
    virus_coalert: str | None
    seasonal_trigger: str | None


_PEST_RULES: dict[PestName, _PestRule] = {
    "spider_mite": _PestRule(
        temp_range=(27.0, 40.0),
        humidity_min=None,
        humidity_max=50.0,
        humidity_logic="max",
        pest_type="mite",
        life_stage_risk="both",
        affected_crops=("corn", "bean", "tomato", "strawberry", "rose", "cucumber", "cotton"),
        name_es="Araña roja",
        scientific_name="Tetranychus urticae / T. cinnabarinus",
        virus_coalert=None,
        seasonal_trigger=None,
    ),
    "whitefly": _PestRule(
        temp_range=(24.0, 32.0),
        humidity_min=50.0,
        humidity_max=80.0,
        humidity_logic="range",
        pest_type="insect",
        life_stage_risk="adult",
        affected_crops=("tomato", "bean", "pepper", "melon", "cucumber", "squash", "cotton"),
        name_es="Mosca blanca",
        scientific_name="Bemisia tabaci / Trialeurodes vaporariorum",
        virus_coalert="BGMV (Bean golden mosaic virus) en frijol",
        seasonal_trigger=None,
    ),
    "broad_mite": _PestRule(
        temp_range=(20.0, 30.0),
        humidity_min=70.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="mite",
        life_stage_risk="both",
        affected_crops=("pepper", "tomato", "bean", "citrus", "papaya"),
        name_es="Ácaro ancho / Ácaro del bronceado",
        scientific_name="Polyphagotarsonemus latus",
        virus_coalert=None,
        seasonal_trigger=None,
    ),
    "white_grub": _PestRule(
        temp_range=(18.0, 28.0),
        humidity_min=60.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="insect",
        life_stage_risk="larva",
        affected_crops=("corn", "sugarcane", "potato", "bean", "pasture", "coffee"),
        name_es="Gallina ciega",
        scientific_name="Phyllophaga spp.",
        virus_coalert=None,
        seasonal_trigger="rainy_season",
    ),
    "thrips": _PestRule(
        temp_range=(25.0, 35.0),
        humidity_min=None,
        humidity_max=70.0,
        humidity_logic="max",
        pest_type="insect",
        life_stage_risk="both",
        affected_crops=("onion", "bean", "tomato", "pepper", "melon", "corn", "rose", "strawberry"),
        name_es="Trips",
        scientific_name="Thrips palmi / Frankliniella occidentalis / F. williamsi",
        virus_coalert="TSWV (Tomato spotted wilt virus) en tomate/cebolla",
        seasonal_trigger=None,
    ),
    "leafminer": _PestRule(
        temp_range=(20.0, 30.0),
        humidity_min=40.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="insect",
        life_stage_risk="larva",
        affected_crops=("tomato", "bean", "potato", "celery", "onion", "melon", "cucumber"),
        name_es="Minador de la hoja",
        scientific_name="Liriomyza sativae / L. trifolii / L. huidobrensis",
        virus_coalert=None,
        seasonal_trigger=None,
    ),
    "fall_armyworm": _PestRule(
        temp_range=(20.0, 30.0),
        humidity_min=60.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="insect",
        life_stage_risk="larva",
        affected_crops=("corn", "sorghum", "sugarcane", "rice", "bean"),
        name_es="Gusano cogollero",
        scientific_name="Spodoptera frugiperda",
        virus_coalert=None,
        seasonal_trigger=None,
    ),
    "root_knot_nematode": _PestRule(
        temp_range=(20.0, 30.0),
        humidity_min=50.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="nematode",
        life_stage_risk="larva",
        affected_crops=("tomato", "pepper", "bean", "carrot", "coffee", "banana", "cucumber"),
        name_es="Nematodo agallador",
        scientific_name="Meloidogyne incognita / M. javanica",
        virus_coalert=None,
        seasonal_trigger=None,
    ),
    "coffee_berry_borer": _PestRule(
        temp_range=(20.0, 30.0),
        humidity_min=75.0,
        humidity_max=None,
        humidity_logic="min",
        pest_type="insect",
        life_stage_risk="adult",
        affected_crops=("coffee",),
        name_es="Broca del café",
        scientific_name="Hypothenemus hampei",
        virus_coalert=None,
        seasonal_trigger=None,
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


def _check_seasonal_trigger(
    rule: _PestRule,
    weather: WeatherResponse,
) -> bool:
    if rule.seasonal_trigger != "rainy_season":
        return False

    if not weather.daily.time:
        return False

    try:
        first_date = weather.daily.time[0]
        if isinstance(first_date, str):
            dt = datetime.fromisoformat(first_date.replace("Z", "+00:00"))
        else:
            dt = first_date
        month = dt.month
    except Exception:
        return False

    if month in (5, 6, 7):
        return rainy_days >= 2 if (rainy_days := sum(
            1 for p in weather.daily.precipitation_sum
            if p is not None and p >= 10.0
        )) else False

    return False


def _score_pest(
    pest: PestName,
    avg_temp: float | None,
    avg_rh: float | None,
    rainy_days: int,
    check_seasonal: bool,
) -> tuple[float, list[str]]:
    rule = _PEST_RULES[pest]
    t_lo, t_hi = rule.temp_range
    score = 0.0
    notes: list[str] = []

    if avg_temp is not None and t_lo <= avg_temp <= t_hi:
        if pest == "spider_mite" and avg_temp >= 30.0:
            score += 0.5
            notes.append(f"T° alta {avg_temp:.1f}°C favorece reproducción")
        elif pest == "spider_mite":
            score += 0.3
            notes.append(
                f"T° media {avg_temp:.1f}°C en rango [{t_lo:.0f}-{t_hi:.0f}°C]"
            )
        elif avg_temp is not None and t_lo <= avg_temp <= t_hi:
            score += 0.4
            notes.append(
                f"T° media {avg_temp:.1f}°C en rango óptimo [{t_lo:.0f}-{t_hi:.0f}°C]"
            )

    humidity_score = 0.0
    if rule.humidity_logic == "min" and avg_rh is not None:
        if rule.humidity_min is not None and avg_rh >= rule.humidity_min:
            humidity_score += 0.3
            notes.append(f"HR {avg_rh:.0f}% ≥ {rule.humidity_min:.0f}% (mín)")
    elif rule.humidity_logic == "max" and avg_rh is not None:
        if rule.humidity_max is not None and avg_rh <= rule.humidity_max:
            humidity_score += 0.4
            notes.append(f"HR {avg_rh:.0f}% ≤ {rule.humidity_max:.0f}% (máx - INVERSA)")
    elif rule.humidity_logic == "range" and avg_rh is not None:
        if (
            rule.humidity_min is not None
            and rule.humidity_max is not None
            and rule.humidity_min <= avg_rh <= rule.humidity_max
        ):
            humidity_score += 0.3
            notes.append(f"HR {avg_rh:.0f}% en rango [{rule.humidity_min:.0f}-{rule.humidity_max:.0f}%]")

    score += humidity_score

    if rule.seasonal_trigger == "rainy_season" and check_seasonal:
        score += 0.3
        notes.append("Inicio de temporada lluviosa: vuelo de adultos")

    if rainy_days >= 3:
        score += 0.2
        notes.append(f"{rainy_days} días con precipitación")

    return score, notes


def _interpret(
    pest: PestName,
    level: RiskLevel,
    factors: PestRiskFactors,
    virus_coalert: str | None,
) -> str:
    rule = _PEST_RULES[pest]
    label = _RISK_LABELS[level]
    reasons = (
        "; ".join(factors.rule_notes)
        if factors.rule_notes
        else "ninguna condición favorable detectada"
    )
    result = f"{label} de {rule.name_es} ({rule.scientific_name}) en los próximos {factors.window_days} días. Factores: {reasons}."

    if virus_coalert and level in ("high", "very_high"):
        result += f" ATENCIÓN: Posible {virus_coalert}."

    return result


async def compute_pest_risk(
    weather_provider: WeatherProvider,
    weather_cache: WeatherCache,
    lat: float,
    lon: float,
    pest: PestName,
) -> PestRiskResponse:
    weather = await fetch_weather(weather_provider, weather_cache, lat, lon)
    avg_temp, avg_rh, rainy_days = _aggregate_weather(weather)

    rule = _PEST_RULES[pest]
    check_seasonal = _check_seasonal_trigger(rule, weather)

    score, notes = _score_pest(pest, avg_temp, avg_rh, rainy_days, check_seasonal)
    level = _risk_level(score)

    virus_coalert = None
    if level in ("high", "very_high") and rule.virus_coalert:
        virus_coalert = rule.virus_coalert

    factors = PestRiskFactors(
        window_days=len(weather.daily.time),
        avg_temp_c=avg_temp,
        avg_humidity_pct=avg_rh,
        rainy_days=rainy_days,
        rule_notes=notes,
    )

    return PestRiskResponse(
        pest=pest,
        pest_type=rule.pest_type,
        life_stage_risk=rule.life_stage_risk,
        affected_crops=list(rule.affected_crops),
        lat=lat,
        lon=lon,
        risk_score=round(score, 2),
        risk_level=level,
        factors=factors,
        virus_coalert=virus_coalert,
        interpretation=_interpret(pest, level, factors, virus_coalert),
    )