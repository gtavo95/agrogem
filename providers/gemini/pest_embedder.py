from google import genai
from google.genai import types

from domain.pest.embedder import EmbeddingError


EMBED_MODEL = "gemini-embedding-2"
EMBED_DIM = 768


class GeminiPestEmbedder:
    """Gemini API adapter for the PestEmbedder port. Uses gemini-embedding-2 multimodal."""

    def __init__(self, client: genai.Client, output_dim: int = EMBED_DIM):
        self._client = client
        self._output_dim = output_dim

    async def embed_image(self, image_bytes: bytes, mime_type: str) -> list[float]:
        try:
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            result = await self._client.aio.models.embed_content(
                model=EMBED_MODEL,
                contents=part,
                config=types.EmbedContentConfig(output_dimensionality=self._output_dim),
            )
        except Exception as e:
            raise EmbeddingError(f"Gemini embed_content failed: {e}") from e

        embeddings = result.embeddings
        if not embeddings or embeddings[0].values is None:
            raise EmbeddingError("Gemini returned no embedding values")
        return list(embeddings[0].values)
