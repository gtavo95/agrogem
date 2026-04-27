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
    "strawberry",
]
RiskLevel = Literal["low", "moderate", "high", "very_high"]


class HarvestWindowFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    window_days: int = Field(description="Días del forecast evaluado.")
    avg_temp_c: float | None = Field(default=None, description="Temperatura media (°C).")
    avg_humidity_pct: float | None = Field(default=None, description="Humedad relativa (%).")
    rainy_days: int = Field(description="Días con precipitación.")
    dry_spells: int = Field(description="Días secos consecutivos.")
    rule_notes: list[str] = Field(default_factory=list, description="Factores detectados.")


class HarvestWindowResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crop: CropName
    lat: float
    lon: float
    window_score: float = Field(ge=0.0, le=1.0, description="Índice 0.0 a 1.0 (1=óptimo).")
    window_level: RiskLevel
    factors: HarvestWindowFactors
    optimal_dates: list[str] = Field(
        description="Fechas óptimas para cosecha."
    )
    warning: str | None = Field(
        default=None, description="Advertencia si condiciones adversas."
    )
    interpretation: str