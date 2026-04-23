from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PestName = Literal[
    "spider_mite",
    "whitefly",
    "broad_mite",
    "white_grub",
    "thrips",
    "leafminer",
    "fall_armyworm",
    "root_knot_nematode",
    "coffee_berry_borer",
]
PestType = Literal["mite", "insect", "nematode"]
LifeStageRisk = Literal["larva", "adult", "both"]
HumidityLogic = Literal["min", "max", "range"]
RiskLevel = Literal["low", "moderate", "high", "very_high"]


class PestRiskFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    window_days: int = Field(description="Duración del forecast evaluado (días).")
    avg_temp_c: float | None = Field(
        default=None, description="Temperatura media horaria en la ventana (°C)."
    )
    avg_humidity_pct: float | None = Field(
        default=None, description="Humedad relativa media horaria (%)."
    )
    rainy_days: int = Field(
        description="Número de días con precipitación ≥ 1 mm en la ventana."
    )
    rule_notes: list[str] = Field(
        default_factory=list,
        description="Condiciones favorables detectadas.",
    )


class PestRiskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pest: PestName
    pest_type: PestType
    life_stage_risk: LifeStageRisk
    affected_crops: list[str]
    lat: float
    lon: float
    risk_score: float = Field(
        ge=0.0, le=1.0, description="Índice compuesto 0.0 a 1.0."
    )
    risk_level: RiskLevel
    factors: PestRiskFactors
    virus_coalert: str | None = Field(
        default=None,
        description="Alerta de virus relacionado cuando aplica.",
    )
    interpretation: str