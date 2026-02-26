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

    # Supabase Auth
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    admin_email: str = ""

    # LLM (Groq) — comma-separated for rotation, single key still works
    groq_api_key: str = ""
    groq_api_keys: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_model_fast: str = "openai/gpt-oss-120b"

    # Google Gemini — comma-separated for rotation, single key still works
    gemini_api_key: str = ""
    gemini_api_keys: str = ""
    gemini_model: str = "gemini-pro"

    @property
    def groq_key_list(self) -> list[str]:
        """Parse GROQ_API_KEYS (comma-separated), fall back to single GROQ_API_KEY."""
        if self.groq_api_keys:
            return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]
        if self.groq_api_key:
            return [self.groq_api_key]
        return []

    @property
    def gemini_key_list(self) -> list[str]:
        """Parse GEMINI_API_KEYS (comma-separated), fall back to single GEMINI_API_KEY."""
        if self.gemini_api_keys:
            return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]
        if self.gemini_api_key:
            return [self.gemini_api_key]
        return []

    # Embeddings (Gemini API)
    embedding_model: str = "gemini"
    embedding_dimension: int = 768

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_rag_results: int = 5
    similarity_threshold: float = 0.3

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
