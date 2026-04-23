from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DiseaseName = Literal[
    "coffee_rust",
    "late_blight",
    "corn_rust",
    "wheat_leaf_rust",
    "wheat_yellow_rust",
    "wheat_stem_rust",
    "sugarbeet_cercospora",
    "sugarbeet_rust",
    "barley_rust",
    "rice_blast",
    "rice_brown_spot",
    "rice_sheath_blight",
    "rice_bacterial_leaf_blight",
    "tomato_early_blight",
    "tomato_late_blight",
    "tomato_fusarium_wilt",
    "potato_late_blight",
    "potato_early_blight",
    "bean_rust",
    "bean_angular_leaf_spot",
    "bean_anthracnose",
    "banana_black_sigatoka",
    "banana_fusarium_wilt",
    "cardamom_rot",
    "sugarcane_rust",
    "sugarcane_smut",
    "sugarcane_red_rot",
    "rose_botrytis",
    "rose_powdery_mildew",
    "rose_downy_mildew",
    "rose_black_spot",
    "cacao_monilia",
    "cacao_black_pod",
    "cacao_witches_broom",
    "cacao_frosty_pod",
    "banana_moko",
    "banana_cordana_leaf_spot",
    "potato_bacterial_wilt",
    "potato_blackleg",
    "oca_downy_mildew",
    "broccoli_downy_mildew",
    "broccoli_black_rot",
    "broccoli_alternaria",
    "oil_palm_bud_rot",
    "oil_palm_spear_rot",
    "oil_palm_ganoderma",
    "corn_gray_leaf_spot",
    "corn_northern_leaf_blight",
    "corn_stalk_rot",
    "coffee_cercospora",
]
RiskLevel = Literal["low", "moderate", "high", "very_high"]
Region = Literal["costa", "sierra", "oriente", "nacional"]


class DiseaseRiskFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    window_days: int = Field(description="Duración del forecast evaluado (días).")
    avg_temp_c: float | None = Field(
        default=None, description="Temperatura media horaria en la ventana (°C)."
    )
    avg_humidity_pct: float | None = Field(
        default=None, description="Humedad relativa media horaria en la ventana (%)."
    )
    rainy_days: int = Field(
        description="Número de días con precipitación ≥ 1 mm en la ventana."
    )
    rule_notes: list[str] = Field(
        default_factory=list,
        description="Condiciones favorables detectadas, en lenguaje natural.",
    )


class DiseaseRiskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    disease: DiseaseName
    lat: float
    lon: float
    risk_score: float = Field(
        ge=0.0, le=1.0, description="Índice compuesto 0.0 (nulo) a 1.0 (máximo)."
    )
    risk_level: RiskLevel
    factors: DiseaseRiskFactors
    interpretation: str
