"""
Orchestrate the full document processing pipeline.
"""
from pathlib import Path
from typing import List, Dict, Any
import logging

from .docx_extractor import DocxExtractor
from .text_chunker import TextChunker
from .embedding_generator import EmbeddingGenerator
from .supabase_loader import SupabaseLoader


logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """
    Full pipeline: DOCX -> Extract -> Chunk -> Embed -> Supabase
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.extractor = DocxExtractor()
        self.chunker = TextChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.embedder = EmbeddingGenerator(embedding_model)
        self.loader = SupabaseLoader(supabase_url, supabase_key)

    def process_directory(
        self,
        directory: Path,
        class_level: int,
        subject: str,
        chapter_metadata: Dict[int, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process all DOCX files in a directory.

        Args:
            directory: Path to directory containing DOCX files
            class_level: Class level (9, 10, 11)
            subject: Subject name (e.g., "Physics")
            chapter_metadata: Optional dict mapping chapter_number to metadata

        Returns:
            Processing results summary
        """
        results = {
            "processed": 0,
            "failed": 0,
            "total_chunks": 0,
            "chapters": [],
        }

        docx_files = sorted(directory.glob("*.docx"))
        logger.info(f"Found {len(docx_files)} DOCX files")

        for file_path in docx_files:
            try:
                chapter_num = self._get_chapter_num(file_path.name)
                meta = (
                    chapter_metadata.get(chapter_num, {})
                    if chapter_metadata
                    else {}
                )

                result = self.process_file(
                    file_path=file_path,
                    class_level=class_level,
                    subject=subject,
                    metadata=meta,
                )
                results["processed"] += 1
                results["total_chunks"] += result["chunks_loaded"]
                results["chapters"].append(result)

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results["failed"] += 1

        return results

    def process_file(
        self,
        file_path: Path,
        class_level: int,
        subject: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process a single DOCX file.

        Args:
            file_path: Path to DOCX file
            class_level: Class level
            subject: Subject name
            metadata: Optional chapter metadata (title, description, topics)

        Returns:
            Processing result for this file
        """
        metadata = metadata or {}
        logger.info(f"Processing: {file_path.name}")

        # Step 1: Extract text and structure
        logger.info("  Step 1: Extracting text...")
        doc = self.extractor.extract(file_path)

        # Step 2: Get or create chapter in Supabase
        chapter_title = metadata.get("title", f"Chapter {doc.chapter_number}")

        chapter_id = self.loader.get_or_create_chapter(
            class_level=class_level,
            subject=subject,
            chapter_number=doc.chapter_number,
            chapter_title=chapter_title,
            description=metadata.get("description", ""),
            topics=metadata.get("topics", []),
            source_file=file_path.name,
        )

        # Clear existing chunks (for re-processing)
        self.loader.clear_chapter_chunks(chapter_id)

        # Step 3: Chunk the document
        logger.info("  Step 2: Chunking document...")
        chunks = self.chunker.chunk_document(
            sections=doc.sections,
            chapter_title=chapter_title,
        )
        logger.info(f"    Created {len(chunks)} chunks")

        # Step 4: Generate embeddings
        logger.info("  Step 3: Generating embeddings...")
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.generate_batch(texts)

        # Step 5: Load to Supabase
        logger.info("  Step 4: Loading to Supabase...")
        load_result = self.loader.load_chunks(
            chapter_id=chapter_id,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.info(f"  Done! Loaded {load_result.chunks_loaded} chunks")

        return {
            "file": file_path.name,
            "chapter_number": doc.chapter_number,
            "chapter_id": chapter_id,
            "chunks_loaded": load_result.chunks_loaded,
            "errors": load_result.errors,
        }

    def _get_chapter_num(self, filename: str) -> int:
        """Extract chapter number from filename."""
        import re

        match = re.search(r"Chapter\s+(\d+)", filename, re.IGNORECASE)
        return int(match.group(1)) if match else 0
