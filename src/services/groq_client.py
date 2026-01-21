"""
Groq API client wrapper.
"""
from groq import Groq
from functools import lru_cache
from ..config import settings


@lru_cache()
def get_groq_client() -> Groq:
    """Get cached Groq client instance."""
    return Groq(api_key=settings.groq_api_key)
