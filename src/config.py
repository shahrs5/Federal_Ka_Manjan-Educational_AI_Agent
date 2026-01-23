"""
Configuration management using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_env: str = "development"
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # Supabase (Vector Store)
    supabase_url: str = ""
    supabase_key: str = ""

    # LLM (Groq)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_model_fast: str = "openai/gpt-oss-120b"

    # Google Gemini (optional)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-pro"

    # Embeddings (use "gemini" for Gemini API, or "sentence-transformers/..." for local)
    embedding_model: str = "gemini"
    embedding_dimension: int = 768

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_rag_results: int = 5
    similarity_threshold: float = 0.5

    # Agent Settings
    max_router_iterations: int = 2
    max_orchestrator_iterations: int = 3  # Legacy from original .env

    # Logging
    log_level: str = "INFO"

    # Database (legacy)
    database_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
