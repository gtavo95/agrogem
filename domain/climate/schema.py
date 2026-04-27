from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Granularity = Literal["daily", "monthly"]


class ClimatePoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: str = Field(description="Día (YYYY-MM-DD) o mes (YYYY-MM).")
    t2m: float | None = Field(default=None, description="Temperatura media a 2m (°C).")
    t2m_max: float | None = Field(default=None, description="Temperatura máxima a 2m (°C).")
    t2m_min: float | None = Field(default=None, description="Temperatura mínima a 2m (°C).")
    precipitation_mm: float | None = Field(
        default=None, description="Precipitación (mm)."
    )
    rh_pct: float | None = Field(default=None, description="Humedad relativa a 2m (%).")
    solar_mj_m2: float | None = Field(
        default=None,
        description="Radiación solar de onda corta (MJ/m²/día para daily, MJ/m²/mes para monthly).",
    )


class ClimateHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    granularity: Granularity
    start: str
    end: str
    series: list[ClimatePoint]
    interpretation: str = ""
