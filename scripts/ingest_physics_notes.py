#!/usr/bin/env python3
"""
Ingest Physics Class 9 notes into Supabase.

Usage:
    python scripts/ingest_physics_notes.py

Requirements:
    - Supabase project with pgvector enabled
    - Run scripts/setup_supabase.sql first
    - Set SUPABASE_URL and SUPABASE_KEY in .env
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import settings
from src.ingestion.pipeline import DocumentIngestionPipeline, PHYSICS_CLASS_9_CHAPTERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the ingestion pipeline for Physics Class 9."""

    # Validate settings
    if not settings.supabase_url or not settings.supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    # Path to Physics notes
    notes_dir = Path(__file__).parent.parent / "Notes" / "Class 9" / "Physics" / "Content"

    if not notes_dir.exists():
        logger.error(f"Notes directory not found: {notes_dir}")
        sys.exit(1)

    logger.info(f"Notes directory: {notes_dir}")
    logger.info(f"Supabase URL: {settings.supabase_url}")

    # Initialize pipeline
    pipeline = DocumentIngestionPipeline(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key,
        embedding_model=settings.embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Process all Physics Class 9 notes
    logger.info("Starting ingestion...")
    results = pipeline.process_directory(
        directory=notes_dir,
        class_level=9,
        subject="Physics",
        chapter_metadata=PHYSICS_CLASS_9_CHAPTERS,
    )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Processed: {results['processed']} files")
    logger.info(f"Failed: {results['failed']} files")
    logger.info(f"Total chunks: {results['total_chunks']}")

    for chapter in results["chapters"]:
        logger.info(
            f"  Chapter {chapter['chapter_number']}: "
            f"{chapter['chunks_loaded']} chunks"
        )
        if chapter["errors"]:
            for error in chapter["errors"]:
                logger.warning(f"    Error: {error}")


if __name__ == "__main__":
    main()
