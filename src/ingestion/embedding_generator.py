"""
Generate embeddings using Gemini or sentence-transformers.
"""
from typing import List
import os


class EmbeddingGenerator:
    """
    Generate embeddings using Gemini API or sentence-transformers.

    Gemini text-embedding-004:
    - 768 dimensional output
    - Excellent quality
    - Free tier: 1500 requests/minute

    Fallback to sentence-transformers if no API key.
    """

    def __init__(
        self,
        model_name: str = "gemini",
        api_key: str = None,
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = None
        self._gemini_client = None

        # Determine which backend to use
        if model_name == "gemini" or model_name.startswith("models/"):
            if not self.api_key:
                print("[WARN] No GEMINI_API_KEY found, falling back to sentence-transformers")
                self.backend = "sentence-transformers"
                self.model_name = "sentence-transformers/all-mpnet-base-v2"
            else:
                self.backend = "gemini"
                self.model_name = "models/text-embedding-004"
        else:
            self.backend = "sentence-transformers"

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        if self.backend == "gemini":
            return 768
        elif "mpnet" in self.model_name or "bge" in self.model_name:
            return 768
        else:
            return 384

    @property
    def gemini_client(self):
        """Lazy load Gemini client."""
        if self._gemini_client is None and self.backend == "gemini":
            import google.genai as genai
            self._gemini_client = genai.Client(api_key=self.api_key)
        return self._gemini_client

    @property
    def model(self):
        """Lazy load sentence-transformers model."""
        if self._model is None and self.backend == "sentence-transformers":
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            List of floats (768 dimensions for Gemini)
        """
        if self.backend == "gemini":
            result = self.gemini_client.models.embed_content(
                model=self.model_name,
                contents=text,
                config={"task_type": "RETRIEVAL_DOCUMENT"},
            )
            return result.embeddings[0].values
        else:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()

    def generate_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding

        Returns:
            List of embeddings
        """
        if self.backend == "gemini":
            # Gemini batch embedding
            embeddings = []
            total_batches = (len(texts) - 1) // batch_size + 1
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                print(f"  Embedding batch {i//batch_size + 1}/{total_batches}...")
                for text in batch:
                    result = self.gemini_client.models.embed_content(
                        model=self.model_name,
                        contents=text,
                        config={"task_type": "RETRIEVAL_DOCUMENT"},
                    )
                    embeddings.append(result.embeddings[0].values)
            return embeddings
        else:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
            return embeddings.tolist()

    def generate_query(self, text: str) -> List[float]:
        """
        Generate embedding for a query (uses retrieval_query task type for Gemini).

        Args:
            text: Query text

        Returns:
            List of floats
        """
        if self.backend == "gemini":
            result = self.gemini_client.models.embed_content(
                model=self.model_name,
                contents=text,
                config={"task_type": "RETRIEVAL_QUERY"},  # Different task type for queries
            )
            return result.embeddings[0].values
        else:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
