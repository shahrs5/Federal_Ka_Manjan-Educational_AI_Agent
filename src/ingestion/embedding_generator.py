"""
Generate embeddings using Gemini API.
"""
from typing import List
import os
import time
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using Gemini API.

    Gemini gemini-embedding-001 (replaced text-embedding-004 on Jan 14, 2026):
    - Default 3072 dims, but configurable (we use 768 for backward compat)
    - Excellent quality, 100+ languages
    - Free tier available
    """

    def __init__(
        self,
        model_name: str = "gemini",
        api_key: str = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._gemini_client = None

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for embeddings")

        self.model_name = "models/gemini-embedding-001"

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return 768

    @property
    def gemini_client(self):
        """Lazy load Gemini client."""
        if self._gemini_client is None:
            import google.genai as genai
            self._gemini_client = genai.Client(api_key=self.api_key)
        return self._gemini_client

    def _gemini_embed(self, text: str, task_type: str, max_retries: int = 8):
        """Call Gemini embed_content with retry + exponential backoff on 429."""
        for attempt in range(max_retries):
            try:
                result = self.gemini_client.models.embed_content(
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
                    wait = min(2 ** attempt, 60)
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
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
