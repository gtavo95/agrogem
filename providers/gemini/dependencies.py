from fastapi import Depends
from google import genai

from domain.pest.embedder import PestEmbedder
from providers.gemini.config import get_gemini
from providers.gemini.pest_embedder import GeminiPestEmbedder


def get_pest_embedder(client: genai.Client = Depends(get_gemini)) -> PestEmbedder:
    return GeminiPestEmbedder(client)
