import uuid
from collections import defaultdict

from domain.pest.embedder import PestEmbedder
from domain.pest.repository import PestRepository
from domain.pest.schema import (
    ConfidenceLabel,
    PestIdentifyResponse,
    TopMatch,
    UploadUrlResponse,
)
from domain.pest.storage import PestStorage


QUERY_PREFIX = "queries/"
QUERY_CONTENT_TYPE = "image/jpeg"
UPLOAD_URL_TTL_SECONDS = 15 * 60

DEFAULT_TOP_K = 5
# Cutoff below which the top weighted class is considered "not in library".
# Calibrate via scripts/calibrate_knn.py before relying on this.
MIN_CONFIDENCE_RATIO = 0.5
HIGH_CONFIDENCE_RATIO = 0.75


def generate_pest_upload_url(storage: PestStorage) -> UploadUrlResponse:
    object_path = f"{QUERY_PREFIX}{uuid.uuid4().hex}.jpg"
    signed_url = storage.generate_upload_url(object_path, QUERY_CONTENT_TYPE)
    return UploadUrlResponse(
        object_path=object_path,
        signed_url=signed_url,
        content_type=QUERY_CONTENT_TYPE,
        expires_in_seconds=UPLOAD_URL_TTL_SECONDS,
    )


async def identify_pest(
    embedder: PestEmbedder,
    storage: PestStorage,
    repo: PestRepository,
    object_path: str,
    k: int = DEFAULT_TOP_K,
) -> PestIdentifyResponse:
    image_bytes = await storage.read_bytes(object_path)
    query_vector = await embedder.embed_image(image_bytes, QUERY_CONTENT_TYPE)
    matches = await repo.search_similar(query_vector, k)

    if not matches:
        return PestIdentifyResponse()

    votes: dict[str, float] = defaultdict(float)
    best_similarity_per_class: dict[str, float] = {}
    for m in matches:
        weight = max(m.similarity, 0.0)
        votes[m.pest_name] += weight
        prev = best_similarity_per_class.get(m.pest_name, -1.0)
        if m.similarity > prev:
            best_similarity_per_class[m.pest_name] = m.similarity

    winner_name, winner_weight = max(votes.items(), key=lambda kv: kv[1])
    total_weight = sum(votes.values())
    ratio = winner_weight / total_weight if total_weight > 0 else 0.0

    top_match: TopMatch | None = None
    if ratio >= MIN_CONFIDENCE_RATIO:
        top_match = TopMatch(
            pest_name=winner_name,
            similarity=best_similarity_per_class[winner_name],
            weighted_score=winner_weight,
            confidence=_label_confidence(ratio),
        )

    return PestIdentifyResponse(
        top_match=top_match,
        alternatives=matches,
        votes=dict(votes),
    )


def _label_confidence(ratio: float) -> ConfidenceLabel:
    if ratio >= HIGH_CONFIDENCE_RATIO:
        return "high"
    if ratio >= MIN_CONFIDENCE_RATIO:
        return "medium"
    return "low"
