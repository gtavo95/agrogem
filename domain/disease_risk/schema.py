from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DiseaseName = Literal["coffee_rust", "late_blight", "corn_rust"]
RiskLevel = Literal["low", "moderate", "high", "very_high"]


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
