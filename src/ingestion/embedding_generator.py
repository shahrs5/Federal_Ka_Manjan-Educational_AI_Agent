"""
Generate embeddings using Gemini API with automatic key rotation.
"""
from typing import List
import os
import time
import logging

from ..services.key_rotator import KeyRotator

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using Gemini API.

    Gemini gemini-embedding-001 (replaced text-embedding-004 on Jan 14, 2026):
    - Default 3072 dims, but configurable (we use 768 for backward compat)
    - Excellent quality, 100+ languages
    - Free tier available

    Supports multiple API keys with automatic rotation on 429.
    """

    def __init__(
        self,
        model_name: str = "gemini",
        api_key: str = None,
        api_keys: list[str] = None,
    ):
        # Build key list: explicit list > single key > env vars
        keys = api_keys or []
        if not keys and api_key:
            keys = [api_key]
        if not keys:
            env_keys = os.getenv("GEMINI_API_KEYS", "")
            if env_keys:
                keys = [k.strip() for k in env_keys.split(",") if k.strip()]
        if not keys:
            single = os.getenv("GEMINI_API_KEY", "")
            if single:
                keys = [single]

        if not keys:
            raise ValueError("At least one Gemini API key is required for embeddings")

        self._rotator = KeyRotator(keys, name="Gemini")
        self._gemini_clients: dict[str, object] = {}
        self.model_name = "models/gemini-embedding-001"

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return 768

    def _get_client(self, key: str):
        """Lazy-load a Gemini client for the given key."""
        if key not in self._gemini_clients:
            import google.genai as genai
            self._gemini_clients[key] = genai.Client(api_key=key)
        return self._gemini_clients[key]

    def _gemini_embed(self, text: str, task_type: str, max_retries: int = 8):
        """Call Gemini embed_content with key rotation + exponential backoff on 429."""
        keys_tried = 0
        total_keys = self._rotator.key_count

        for attempt in range(max_retries):
            client = self._get_client(self._rotator.current_key)
            try:
                result = client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                    config={
                        "task_type": task_type,
                        "output_dimensionality": 768,
                    },
                )
                return result.embeddings[0].values
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    keys_tried += 1
                    self._rotator.next()

                    if keys_tried >= total_keys:
                        # All keys hit — backoff before next round
                        wait = min(2 ** (attempt - total_keys + 1), 60)
                        logger.warning(
                            f"All {total_keys} Gemini keys rate-limited, "
                            f"backing off {wait}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait)
                        keys_tried = 0
                    # else: rotated to a fresh key, retry immediately
                else:
                    raise
        raise RuntimeError(f"Failed after {max_retries} retries due to rate limiting")

    def generate(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self._gemini_embed(text, "RETRIEVAL_DOCUMENT")

    def generate_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        total_batches = (len(texts) - 1) // batch_size + 1
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"  Embedding batch {i//batch_size + 1}/{total_batches}...")
            for text in batch:
                emb = self._gemini_embed(text, "RETRIEVAL_DOCUMENT")
                embeddings.append(emb)
                time.sleep(1.5)  # ~40 RPM, safe for free tier
        return embeddings

    def generate_query(self, text: str) -> List[float]:
        """Generate embedding for a query (uses retrieval_query task type)."""
        return self._gemini_embed(text, "RETRIEVAL_QUERY")
