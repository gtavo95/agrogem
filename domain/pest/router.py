from fastapi import APIRouter, Depends, HTTPException, status

from domain.pest.embedder import EmbeddingError, PestEmbedder
from domain.pest.repository import PestRepository
from domain.pest.schema import (
    PestIdentifyRequest,
    PestIdentifyResponse,
    UploadUrlResponse,
)
from domain.pest.service import generate_pest_upload_url, identify_pest
from domain.pest.storage import PestStorage, StorageError
from providers.gcs.dependencies import get_pest_storage
from providers.gemini.dependencies import get_pest_embedder
from providers.mongo.dependencies import get_pest_repository


router = APIRouter(prefix="/pest", tags=["pest"])


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_pest_upload_url(
    storage: PestStorage = Depends(get_pest_storage),
):
    "Genera una URL firmada (PUT, ~15 min) para subir una imagen al prefijo `queries/`. El cliente luego llama a `/pest/identify` con el `object_path` devuelto."
    try:
        return generate_pest_upload_url(storage)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage error: {e}",
        )


@router.post("/identify", response_model=PestIdentifyResponse)
async def identify_pest_from_path(
    data: PestIdentifyRequest,
    embedder: PestEmbedder = Depends(get_pest_embedder),
    storage: PestStorage = Depends(get_pest_storage),
    repo: PestRepository = Depends(get_pest_repository),
):
    "Clasifica una plaga buscando vecinos en la biblioteca `pest_embeddings` (kNN ponderado por similitud). Pensado como tool para el agente: el modelo recibe top_match + alternativas + votos para razonar con la evidencia en vez de solo recibir IDs."
    try:
        return await identify_pest(embedder, storage, repo, data.object_path)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage error: {e}",
        )
    except EmbeddingError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding error: {e}",
        )
