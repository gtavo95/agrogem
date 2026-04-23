from pydantic import BaseModel, ConfigDict, Field


class SoilHorizon(BaseModel):
    model_config = ConfigDict(extra="ignore")

    depth: str = Field(description="Rango de profundidad. Ej: '0-5cm'.")
    ph: float | None = Field(default=None, description="pH en H2O.")
    soc_g_per_kg: float | None = Field(
        default=None, description="Carbono orgánico del suelo (g/kg)."
    )
    nitrogen_g_per_kg: float | None = Field(
        default=None, description="Nitrógeno total (g/kg)."
    )
    clay_pct: float | None = Field(default=None, description="% arcilla (0-100).")
    sand_pct: float | None = Field(default=None, description="% arena (0-100).")
    silt_pct: float | None = Field(default=None, description="% limo (0-100).")
    cec_mmol_per_kg: float | None = Field(
        default=None,
        description="Capacidad de intercambio catiónico (mmol(c)/kg).",
    )
    texture_class: str | None = Field(
        default=None,
        description="Clase textural USDA (sandy loam, clay loam, etc.).",
    )


class SoilResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float
    lon: float
    horizons: list[SoilHorizon]
    dominant_texture: str | None = Field(
        default=None,
        description="Clase textural del horizonte superficial (0-5cm).",
    )
    interpretation: str = Field(
        description="Resumen agronómico en lenguaje natural."
    )
