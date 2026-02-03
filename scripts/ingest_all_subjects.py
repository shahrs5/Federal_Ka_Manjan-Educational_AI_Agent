#!/usr/bin/env python3
"""
Ingest all Class 9 subjects into Supabase.

This script processes all subjects: Physics, Chemistry, Biology,
Computer Science, and English.

Usage:
    python scripts/ingest_all_subjects.py

    # Or ingest specific subjects:
    python scripts/ingest_all_subjects.py --subjects Physics Chemistry

Requirements:
    - Supabase project with pgvector enabled
    - Run scripts/setup_supabase.sql first
    - Set SUPABASE_URL and SUPABASE_KEY in .env
"""
import sys
import logging
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import settings
from src.ingestion.pipeline import DocumentIngestionPipeline
from src.ingestion.subject_metadata import SUBJECT_METADATA

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_subject(
    pipeline: DocumentIngestionPipeline,
    subject: str,
    class_level: int = 9,
    base_notes_dir: Path = None,
):
    """
    Ingest a single subject.

    Args:
        pipeline: Ingestion pipeline instance
        subject: Subject name (e.g., "Physics", "Chemistry")
        class_level: Class level (default: 9)
        base_notes_dir: Base directory for notes

    Returns:
        Processing results summary
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"INGESTING: {subject} - Class {class_level}")
    logger.info(f"{'='*60}")

    # Get subject metadata for the specific class level
    chapter_metadata = SUBJECT_METADATA.get(class_level, {}).get(subject)
    if not chapter_metadata:
        logger.warning(f"No metadata found for {subject} Class {class_level}, proceeding without it")

    # Path to subject notes
    notes_dir = base_notes_dir / f"Class {class_level}" / subject / "Content"

    if not notes_dir.exists():
        logger.error(f"Notes directory not found: {notes_dir}")
        return None

    logger.info(f"Notes directory: {notes_dir}")

    # Count files
    docx_files = list(notes_dir.glob("*.docx"))
    logger.info(f"Found {len(docx_files)} DOCX files")

    if not docx_files:
        logger.warning(f"No DOCX files found in {notes_dir}")
        return None

    # Process all files
    results = pipeline.process_directory(
        directory=notes_dir,
        class_level=class_level,
        subject=subject,
        chapter_metadata=chapter_metadata,
    )

    # Print summary
    logger.info("\n" + "-" * 60)
    logger.info(f"{subject} COMPLETE")
    logger.info("-" * 60)
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

    return results


def main():
    """Run the ingestion pipeline for all subjects."""

    # Parse arguments
    parser = argparse.ArgumentParser(description="Ingest Class 9 subjects into Supabase")
    parser.add_argument(
        "--subjects",
        nargs="+",
        choices=["Physics", "Chemistry", "Biology", "Computer Science", "English", "all"],
        default=["all"],
        help="Subjects to ingest (default: all)",
    )
    parser.add_argument(
        "--class-level",
        type=int,
        default=9,
        choices=[9, 10, 11],
        help="Class level (default: 9)",
    )
    args = parser.parse_args()

    # Validate settings
    if not settings.supabase_url or not settings.supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    # Base notes directory
    base_notes_dir = Path(__file__).parent.parent / "Notes"

    if not base_notes_dir.exists():
        logger.error(f"Notes directory not found: {base_notes_dir}")
        sys.exit(1)

    logger.info(f"Base notes directory: {base_notes_dir}")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    logger.info(f"Embedding model: {settings.embedding_model}")

    # Determine which subjects to process
    if "all" in args.subjects:
        subjects_to_process = list(SUBJECT_METADATA.get(args.class_level, {}).keys())
    else:
        subjects_to_process = args.subjects

    logger.info(f"\nSubjects to process: {', '.join(subjects_to_process)}")

    # Initialize pipeline
    pipeline = DocumentIngestionPipeline(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key,
        embedding_model=settings.embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Process each subject
    all_results = {}
    for subject in subjects_to_process:
        try:
            results = ingest_subject(
                pipeline=pipeline,
                subject=subject,
                class_level=args.class_level,
                base_notes_dir=base_notes_dir,
            )
            if results:
                all_results[subject] = results
        except Exception as e:
            logger.error(f"Failed to process {subject}: {e}")
            import traceback
            traceback.print_exc()

    # Print overall summary
    logger.info("\n" + "=" * 60)
    logger.info("ALL SUBJECTS INGESTION COMPLETE")
    logger.info("=" * 60)

    total_processed = sum(r["processed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    total_chunks = sum(r["total_chunks"] for r in all_results.values())

    logger.info(f"Total subjects processed: {len(all_results)}")
    logger.info(f"Total files processed: {total_processed}")
    logger.info(f"Total files failed: {total_failed}")
    logger.info(f"Total chunks created: {total_chunks}")

    logger.info("\nPer-subject summary:")
    for subject, results in all_results.items():
        logger.info(
            f"  {subject}: {results['processed']} files, "
            f"{results['total_chunks']} chunks"
        )


if __name__ == "__main__":
    main()
