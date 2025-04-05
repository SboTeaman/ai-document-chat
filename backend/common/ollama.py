from django.conf import settings
from openai import OpenAI


def get_ollama_client() -> OpenAI:
    """Build an OpenAI-compatible client pointed at the local Ollama server."""
    return OpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",
        max_retries=settings.OLLAMA_MAX_RETRIES,
    )
