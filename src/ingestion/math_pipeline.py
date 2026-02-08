"""
Orchestrate Math note ingestion:  .tex -> extract -> chunk -> embed -> Supabase.
"""
from pathlib import Path
from typing import Dict, Any, List
import logging
import re

from .latex_extractor import LatexExtractor
from .math_chunker import MathChunker
from .embedding_generator import EmbeddingGenerator
from .supabase_loader import SupabaseLoader

logger = logging.getLogger(__name__)


class MathIngestionPipeline:
    """
    Full pipeline for Math .tex files.

    Unlike the generic DocumentIngestionPipeline, this uses
    LatexExtractor + MathChunker and handles the fact that a single
    chapter may have many exercise files (each producing its own set of
    chunks that share the same chapter_id).
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        embedding_model: str = "gemini",
    ):
        self.extractor = LatexExtractor()
        self.chunker = MathChunker()
        self.embedder = EmbeddingGenerator(embedding_model)
        self.loader = SupabaseLoader(supabase_url, supabase_key)

    # ------------------------------------------------------------------

    def process_directory(
        self,
        directory: Path,
        class_level: int,
        chapter_metadata: Dict[int, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "processed": 0,
            "failed": 0,
            "total_chunks": 0,
            "chapters": [],
        }

        tex_files = sorted(directory.glob("*.tex"))
        logger.info(f"Found {len(tex_files)} .tex files in {directory}")

        for fp in tex_files:
            try:
                r = self.process_file(
                    file_path=fp,
                    class_level=class_level,
                    chapter_metadata=chapter_metadata,
                )
                results["processed"] += 1
                results["total_chunks"] += r["chunks_loaded"]
                results["chapters"].append(r)
            except Exception as e:
                logger.error(f"Failed to process {fp.name}: {e}")
                results["failed"] += 1

        return results

    # ------------------------------------------------------------------

    def process_file(
        self,
        file_path: Path,
        class_level: int,
        chapter_metadata: Dict[int, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chapter_metadata = chapter_metadata or {}
        logger.info(f"Processing: {file_path.name}")

        # 1. Extract
        doc = self.extractor.extract(file_path)
        meta = chapter_metadata.get(doc.chapter_number, {})
        chapter_title = meta.get("title", f"Chapter {doc.chapter_number}")
        exercise_title = doc.metadata.get("exercise_title", "")

        # 2. Get or create chapter record (shared across exercises)
        chapter_id = self.loader.get_or_create_chapter(
            class_level=class_level,
            subject="Math",
            chapter_number=doc.chapter_number,
            chapter_title=chapter_title,
            description=meta.get("description", ""),
            topics=meta.get("topics", []),
            source_file=file_path.name,
        )

        # 3. Figure out chunk_index offset so we don't collide with
        #    chunks from other exercise files of the same chapter.
        offset = self._get_max_chunk_index(chapter_id) + 1

        # 4. Chunk
        chunks = self.chunker.chunk_document(
            sections=doc.sections,
            chapter_title=chapter_title,
            class_level=class_level,
            exercise_title=exercise_title,
        )
        # Apply offset
        for c in chunks:
            c.chunk_index += offset

        logger.info(f"  {len(chunks)} chunks (offset {offset})")

        if not chunks:
            return {
                "file": file_path.name,
                "chapter_number": doc.chapter_number,
                "chapter_id": chapter_id,
                "chunks_loaded": 0,
                "errors": [],
            }

        # 5. Embed
        texts = [c.text for c in chunks]
        embeddings = self.embedder.generate_batch(texts)

        # 6. Load
        load_result = self.loader.load_chunks(
            chapter_id=chapter_id,
            chunks=chunks,
            embeddings=embeddings,
        )
        logger.info(f"  Loaded {load_result.chunks_loaded} chunks")

        return {
            "file": file_path.name,
            "chapter_number": doc.chapter_number,
            "chapter_id": chapter_id,
            "chunks_loaded": load_result.chunks_loaded,
            "errors": load_result.errors,
        }

    # ------------------------------------------------------------------

    def _get_max_chunk_index(self, chapter_id: str) -> int:
        """Return the highest chunk_index already stored for *chapter_id*, or -1."""
        try:
            result = (
                self.loader.client.table("document_chunks")
                .select("chunk_index")
                .eq("chapter_id", chapter_id)
                .order("chunk_index", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]["chunk_index"]
        except Exception:
            pass
        return -1
