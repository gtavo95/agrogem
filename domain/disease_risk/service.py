from dataclasses import dataclass
from statistics import mean

from domain.disease_risk.schema import (
    DiseaseName,
    DiseaseRiskFactors,
    DiseaseRiskResponse,
    RiskLevel,
    Region,
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
    region: Region


_DISEASE_RULES: dict[DiseaseName, _DiseaseRule] = {
    "coffee_rust": _DiseaseRule(
        temp_range=(21.0, 25.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="roya del café (Hemileia vastatrix)",
        region="nacional",
    ),
    "late_blight": _DiseaseRule(
        temp_range=(10.0, 25.0),
        rh_threshold=85.0,
        rainy_days_threshold=4,
        name_es="tizón tardío (Phytophthora infestans)",
        region="nacional",
    ),
    "corn_rust": _DiseaseRule(
        temp_range=(15.5, 24.5),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="roya común del maíz (Puccinia sorghi)",
        region="nacional",
    ),
    "wheat_leaf_rust": _DiseaseRule(
        temp_range=(15.0, 20.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="roya de la hoja del trigo (Puccinia triticina)",
        region="sierra",
    ),
    "wheat_yellow_rust": _DiseaseRule(
        temp_range=(10.0, 15.0),
        rh_threshold=100.0,
        rainy_days_threshold=3,
        name_es="roya amarela del trigo (Puccinia striiformis)",
        region="sierra",
    ),
    "wheat_stem_rust": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="roya del tallo del trigo (Puccinia graminis)",
        region="sierra",
    ),
    "sugarbeet_cercospora": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="cercospora de la remolacha (Cercospora beticola)",
        region="sierra",
    ),
    "sugarbeet_rust": _DiseaseRule(
        temp_range=(15.0, 20.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="roya de la remolacha (Uromyces betae)",
        region="sierra",
    ),
    "barley_rust": _DiseaseRule(
        temp_range=(15.0, 22.0),
        rh_threshold=100.0,
        rainy_days_threshold=3,
        name_es="roya de la cebada (Puccinia hordei)",
        region="sierra",
    ),
    "rice_blast": _DiseaseRule(
        temp_range=(24.0, 28.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="piricularia del arroz (Pyricularia oryzae)",
        region="costa",
    ),
    "rice_brown_spot": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="mancha marrón del arroz (Bipolaris oryzae)",
        region="costa",
    ),
    "rice_sheath_blight": _DiseaseRule(
        temp_range=(28.0, 32.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="añublo de la vaina del arroz (Rhizoctonia solani)",
        region="costa",
    ),
    "rice_bacterial_leaf_blight": _DiseaseRule(
        temp_range=(25.0, 34.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="marchitamiento bacteriano de la hoja del arroz (Xanthomonas oryzae)",
        region="costa",
    ),
    "tomato_early_blight": _DiseaseRule(
        temp_range=(24.0, 29.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="tizón temprano del tomate (Alternaria solani)",
        region="nacional",
    ),
    "tomato_late_blight": _DiseaseRule(
        temp_range=(10.0, 20.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="tizón tardío del tomate (Phytophthora infestans)",
        region="nacional",
    ),
    "tomato_fusarium_wilt": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=70.0,
        rainy_days_threshold=3,
        name_es="marchitamiento por fusarium del tomate (Fusarium oxysporum)",
        region="nacional",
    ),
    "potato_late_blight": _DiseaseRule(
        temp_range=(10.0, 20.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="tizón tardío de la papa (Phytophthora infestans)",
        region="sierra",
    ),
    "potato_early_blight": _DiseaseRule(
        temp_range=(20.0, 30.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="tizón temprano de la papa (Alternaria solani)",
        region="sierra",
    ),
    "bean_rust": _DiseaseRule(
        temp_range=(16.0, 22.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="roya del frijol (Uromyces appendiculatus)",
        region="nacional",
    ),
    "bean_angular_leaf_spot": _DiseaseRule(
        temp_range=(16.0, 28.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="mancha angular de la hoja del frijol (Phaeoisariopsis griseola)",
        region="nacional",
    ),
    "bean_anthracnose": _DiseaseRule(
        temp_range=(13.0, 26.0),
        rh_threshold=92.0,
        rainy_days_threshold=3,
        name_es="antracnosis del frijol (Colletotrichum lindemuthianum)",
        region="nacional",
    ),
    "banana_black_sigatoka": _DiseaseRule(
        temp_range=(26.0, 34.0),
        rh_threshold=95.0,
        rainy_days_threshold=3,
        name_es="sigatoka negra del plátano (Mycosphaerella fijiensis)",
        region="costa",
    ),
    "banana_fusarium_wilt": _DiseaseRule(
        temp_range=(24.0, 32.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="marchitamiento por fusarium del plátano (Fusarium oxysporum f.sp. cubense)",
        region="costa",
    ),
    "cardamom_rot": _DiseaseRule(
        temp_range=(20.0, 30.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="pudrición del cardamomo (Pythium vexans)",
        region="oriente",
    ),
    "sugarcane_rust": _DiseaseRule(
        temp_range=(18.0, 28.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="roya de la caña de azúcar (Puccinia melanocephala)",
        region="costa",
    ),
    "sugarcane_smut": _DiseaseRule(
        temp_range=(25.0, 35.0),
        rh_threshold=70.0,
        rainy_days_threshold=3,
        name_es="carbón de la caña de azúcar (Sporisorium scitamineum)",
        region="costa",
    ),
    "sugarcane_red_rot": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="roya roja de la caña de azúcar (Colletotrichum falcatum)",
        region="costa",
    ),
    "rose_botrytis": _DiseaseRule(
        temp_range=(15.0, 22.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="botritis de la rosa (Botrytis cinerea)",
        region="sierra",
    ),
    "rose_powdery_mildew": _DiseaseRule(
        temp_range=(17.0, 25.0),
        rh_threshold=50.0,
        rainy_days_threshold=3,
        name_es="oidio de la rosa (Sphaerotheca pannosa)",
        region="sierra",
    ),
    "rose_downy_mildew": _DiseaseRule(
        temp_range=(5.0, 18.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="mildeo velloso de la rosa (Peronospora sparsa)",
        region="sierra",
    ),
    "rose_black_spot": _DiseaseRule(
        temp_range=(18.0, 24.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="mancha negra de la rosa (Diplocarpon rosae)",
        region="sierra",
    ),
    "cacao_monilia": _DiseaseRule(
        temp_range=(22.0, 30.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="monilia del cacao (Moniliophthora roreri)",
        region="costa",
    ),
    "cacao_black_pod": _DiseaseRule(
        temp_range=(22.0, 28.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="pudrición negra de la vaina del cacao (Phytophthora palmivora)",
        region="costa",
    ),
    "cacao_witches_broom": _DiseaseRule(
        temp_range=(20.0, 28.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="escoba de bruja del cacao (Moniliophthora perniciosa)",
        region="costa",
    ),
    "cacao_frosty_pod": _DiseaseRule(
        temp_range=(22.0, 30.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="monilia del cacao (Moniliophthora roreri)",
        region="costa",
    ),
    "banana_moko": _DiseaseRule(
        temp_range=(25.0, 35.0),
        rh_threshold=75.0,
        rainy_days_threshold=3,
        name_es="moko del plátano (Ralstonia solanacearum)",
        region="costa",
    ),
    "banana_cordana_leaf_spot": _DiseaseRule(
        temp_range=(22.0, 30.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="mancha cordana del plátano (Cordana musae)",
        region="costa",
    ),
    "potato_bacterial_wilt": _DiseaseRule(
        temp_range=(20.0, 35.0),
        rh_threshold=70.0,
        rainy_days_threshold=3,
        name_es="marchitamiento bacteriano de la papa (Ralstonia solanacearum)",
        region="sierra",
    ),
    "potato_blackleg": _DiseaseRule(
        temp_range=(15.0, 25.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="pierna negra de la papa (Pectobacterium atrosepticum)",
        region="sierra",
    ),
    "oca_downy_mildew": _DiseaseRule(
        temp_range=(10.0, 18.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="mildeo velloso de la oca (Peronospora oxalidis)",
        region="sierra",
    ),
    "broccoli_downy_mildew": _DiseaseRule(
        temp_range=(8.0, 16.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="mildeo velloso del brócoli (Peronospora parasitica)",
        region="sierra",
    ),
    "broccoli_black_rot": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="pudrición negra del brócoli (Xanthomonas campestris)",
        region="sierra",
    ),
    "broccoli_alternaria": _DiseaseRule(
        temp_range=(18.0, 25.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="alternaria del brócoli (Alternaria brassicicola)",
        region="sierra",
    ),
    "oil_palm_bud_rot": _DiseaseRule(
        temp_range=(24.0, 32.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="pudrición del cogollo de la palma aceitera (Phytophthora palmivora)",
        region="costa",
    ),
    "oil_palm_spear_rot": _DiseaseRule(
        temp_range=(26.0, 34.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="pudrición de la flecha de la palma aceitera (Erwinia/Phytophthora)",
        region="costa",
    ),
    "oil_palm_ganoderma": _DiseaseRule(
        temp_range=(25.0, 32.0),
        rh_threshold=80.0,
        rainy_days_threshold=3,
        name_es="ganoderma de la palma aceitera (Ganoderma boninense)",
        region="costa",
    ),
    "corn_gray_leaf_spot": _DiseaseRule(
        temp_range=(22.0, 30.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="mancha gris del maíz (Cercospora zeina)",
        region="nacional",
    ),
    "corn_northern_leaf_blight": _DiseaseRule(
        temp_range=(18.0, 27.0),
        rh_threshold=90.0,
        rainy_days_threshold=3,
        name_es="tizón septum del maíz (Exserohilum turcicum)",
        region="nacional",
    ),
    "corn_stalk_rot": _DiseaseRule(
        temp_range=(25.0, 30.0),
        rh_threshold=75.0,
        rainy_days_threshold=3,
        name_es="pudrición del tallo del maíz (Fusarium verticillioides)",
        region="nacional",
    ),
    "coffee_cercospora": _DiseaseRule(
        temp_range=(20.0, 28.0),
        rh_threshold=85.0,
        rainy_days_threshold=3,
        name_es="cercospora del café (Cercospora coffeicola)",
        region="nacional",
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
