from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.disease_risk.schema import DiseaseName, DiseaseRiskResponse
from domain.disease_risk.service import compute_disease_risk
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/disease-risk", tags=["disease-risk"])


@router.get("", response_model=DiseaseRiskResponse)
async def get_disease_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    disease: DiseaseName = Query(
        ...,
        description="coffee_rust | late_blight | corn_rust | wheat_leaf_rust | wheat_yellow_rust | wheat_stem_rust | sugarbeet_cercospora | sugarbeet_rust | barley_rust | rice_blast | rice_brown_spot | rice_sheath_blight | rice_bacterial_leaf_blight | tomato_early_blight | tomato_late_blight | tomato_fusarium_wilt | potato_late_blight | potato_early_blight | bean_rust | bean_angular_leaf_spot | bean_anthracnose | banana_black_sigatoka | banana_fusarium_wilt | cardamom_rot | sugarcane_rust | sugarcane_smut | sugarcane_red_rot | rose_botrytis | rose_powdery_mildew | rose_downy_mildew | rose_black_spot | cacao_monilia | cacao_black_pod | cacao_witches_broom | cacao_frosty_pod | banana_moko | banana_cordana_leaf_spot | potato_bacterial_wilt | potato_blackleg | oca_downy_mildew | broccoli_downy_mildew | broccoli_black_rot | broccoli_alternaria | oil_palm_bud_rot | oil_palm_spear_rot | oil_palm_ganoderma | corn_gray_leaf_spot | corn_northern_leaf_blight | corn_stalk_rot | coffee_cercospora",
    ),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
):
    "Índice de riesgo de enfermedad (0.0-1.0) para los próximos 7 días. Combina el forecast de /weather con reglas agronómicas específicas por enfermedad. Sin cache propio (reusa el del weather)."
    try:
        return await compute_disease_risk(
            weather_provider, weather_cache, lat, lon, disease
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )
