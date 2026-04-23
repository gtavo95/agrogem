from typing import Literal

from pydantic import BaseModel, Field


ConfidenceLabel = Literal["high", "medium", "low"]


class PestMatch(BaseModel):
    pest_name: str
    similarity: float = Field(ge=-1.0, le=1.0)
    image_id: str | None = None


class TopMatch(BaseModel):
    pest_name: str
    similarity: float
    weighted_score: float
    confidence: ConfidenceLabel


class UploadUrlResponse(BaseModel):
    object_path: str = Field(description="Path en el bucket al que el cliente debe hacer PUT.")
    signed_url: str = Field(description="URL firmada (v4) para subir el binario. Expira en minutos.")
    content_type: str = Field(description="Content-Type que el cliente debe usar en el PUT.")
    expires_in_seconds: int


class PestIdentifyRequest(BaseModel):
    object_path: str = Field(
        min_length=1,
        description="Path GCS previamente obtenido vía /pest/upload-url.",
    )


class PestIdentifyResponse(BaseModel):
    top_match: TopMatch | None = Field(
        default=None,
        description="Mejor match por voto ponderado. Null si ningún match supera el piso mínimo.",
    )
    alternatives: list[PestMatch] = Field(
        default_factory=list,
        description="Top-K vecinos ordenados por similitud (incluye al top_match).",
    )
    votes: dict[str, float] = Field(
        default_factory=dict,
        description="Suma de similitud por pest_name entre los top-K (peso total por clase).",
    )
