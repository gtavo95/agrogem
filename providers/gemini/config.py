from fastapi import Request
from google import genai


def create_gemini_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def get_gemini(request: Request) -> genai.Client:
    """Dependency to retrieve the Gemini client from app state."""
    return request.app.state.gemini
