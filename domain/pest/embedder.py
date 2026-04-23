from typing import Protocol


class EmbeddingError(Exception):
    """Raised when the embedding provider fails."""


class PestEmbedder(Protocol):
    """Port: contract any multimodal embedder must satisfy.

    Embeddings must be compatible with those stored in `pest_embeddings`
    (same model, same output dimensionality) for similarity search to be meaningful.
    """

    async def embed_image(self, image_bytes: bytes, mime_type: str) -> list[float]: ...
