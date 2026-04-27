from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CropName = Literal[
    "corn",
    "rice",
    "bean",
    "wheat",
    "coffee",
    "sugarcane",
    "banana",
    "tomato",
    "potato",
    "onion",
    "broccoli",
    "rose",
]
RiskLevel = Literal["low", "moderate", "high", "very_high"]


class IrrigationRiskFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    window_days: int = Field(description="Días del forecast evaluado.")
    et0_sum_mm: float = Field(description="Evapotranspiración de referencia total (mm).")
    precipitation_sum_mm: float = Field(
        description="Precipitación total forecast (mm)."
    )
    crop_water_requirement_mm: float = Field(
        description="Necesidad hídrica del cultivo (mm)."
    )
    soil_water_deficit_mm: float = Field(
        description="Déficit de agua en el suelo (mm)."
    )
    rule_notes: list[str] = Field(
        default_factory=list, description="Factores detectados."
    )


class IrrigationRiskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crop: CropName
    lat: float
    lon: float
    risk_score: float = Field(ge=0.0, le=1.0, description="Índice 0.0 a 1.0.")
    risk_level: RiskLevel
    factors: IrrigationRiskFactors
    irrigation_recommendation_mm: float = Field(
        description="Agua recomendada a aplicar (mm)."
    )
    interpretation: str