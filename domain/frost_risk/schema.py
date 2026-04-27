from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["low", "moderate", "high", "very_high"]


class FrostRiskFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    window_days: int = Field(description="Días del forecast evaluado.")
    min_temp_c: float | None = Field(default=None, description="Temperatura mínima forecast (°C).")
    frost_hours: int = Field(description="Horas con T° < 0°C en la ventana.")
    freezing_probability_pct: float = Field(
        default=0.0, description="Probabilidad de helada (%)."
    )
    altitude_correction_c: float = Field(
        default=0.0, description="Corrección por elevación (°C)."
    )
    rule_notes: list[str] = Field(default_factory=list, description="Factores detectados.")


class FrostRiskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    elevation_m: float | None = Field(default=None, description="Elevación (m).")
    risk_score: float = Field(ge=0.0, le=1.0, description="Índice 0.0 a 1.0.")
    risk_level: RiskLevel
    factors: FrostRiskFactors
    interpretation: str