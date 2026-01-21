"""
Load processed chunks into Supabase with pgvector.
"""
from typing import List, Dict, Any
from dataclasses import dataclass

from .text_chunker import Chunk


@dataclass
class LoadResult:
    """Result of loading operation."""

    chunks_loaded: int
    chapter_id: str
    errors: List[str]


class SupabaseLoader:
    """
    Load chunks and embeddings into Supabase.

    Uses the Supabase Python client for database operations.
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        from supabase import create_client, Client

        self.client: Client = create_client(supabase_url, supabase_key)

    def get_or_create_chapter(
        self,
        class_level: int,
        subject: str,
        chapter_number: int,
        chapter_title: str,
        description: str = "",
        topics: List[str] = None,
        source_file: str = "",
    ) -> str:
        """
        Get existing chapter or create new one.

        Returns:
            Chapter UUID
        """
        # Check if chapter exists
        result = (
            self.client.table("chapters")
            .select("id")
            .eq("class_level", class_level)
            .eq("subject", subject)
            .eq("chapter_number", chapter_number)
            .execute()
        )

        if result.data:
            return result.data[0]["id"]

        # Create new chapter
        data = {
            "class_level": class_level,
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "chapter_description": description,
            "topics": topics or [],
            "source_file": source_file,
        }

        result = self.client.table("chapters").insert(data).execute()
        return result.data[0]["id"]

    def load_chunks(
        self,
        chapter_id: str,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> LoadResult:
        """
        Load chunks with embeddings into Supabase.

        Args:
            chapter_id: UUID of the chapter
            chunks: List of Chunk objects
            embeddings: List of embedding vectors

        Returns:
            LoadResult with stats
        """
        errors = []
        loaded = 0

        # Prepare batch insert data
        batch_data = []
        for chunk, embedding in zip(chunks, embeddings):
            batch_data.append(
                {
                    "chapter_id": chapter_id,
                    "chunk_text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "embedding": embedding,
                    "metadata": chunk.metadata,
                }
            )

        # Insert in batches of 100
        batch_size = 100
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]
            try:
                self.client.table("document_chunks").insert(batch).execute()
                loaded += len(batch)
            except Exception as e:
                errors.append(f"Batch {i // batch_size}: {str(e)}")

        return LoadResult(
            chunks_loaded=loaded,
            chapter_id=chapter_id,
            errors=errors,
        )

    def clear_chapter_chunks(self, chapter_id: str):
        """Delete all chunks for a chapter (for re-processing)."""
        self.client.table("document_chunks").delete().eq(
            "chapter_id", chapter_id
        ).execute()

    def get_chapter_by_number(
        self, class_level: int, subject: str, chapter_number: int
    ) -> Dict[str, Any] | None:
        """Get chapter by number."""
        result = (
            self.client.table("chapters")
            .select("*")
            .eq("class_level", class_level)
            .eq("subject", subject)
            .eq("chapter_number", chapter_number)
            .execute()
        )

        return result.data[0] if result.data else None
