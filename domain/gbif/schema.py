from pydantic import BaseModel, ConfigDict, Field


class GbifQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scientific_name: str = Field(
        ...,
        min_length=2,
        description="Nombre científico binomial. Ej: 'Spodoptera frugiperda'.",
    )
    country: str = Field(
        default="GT",
        min_length=2,
        max_length=2,
        description="Código ISO alpha-2 del país. Ej: 'GT'.",
    )
    limit: int = Field(
        default=300,
        ge=1,
        le=300,
        description="Tamaño de la muestra de ocurrencias (máximo 300 por llamada a GBIF).",
    )


class CommonName(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    lang: str | None = None


class SpeciesOccurrenceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    found: bool
    scientific_name: str | None = None
    kingdom: str | None = None
    family: str | None = None
    common_names: list[CommonName] = Field(default_factory=list)
    country: str
    total_records_in_country: int = 0
    records_in_sample: int = 0
    top_regions: list[tuple[str, int]] = Field(default_factory=list)
    recent_years: dict[str, int] = Field(default_factory=dict)
    interpretation: str
