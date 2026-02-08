#!/usr/bin/env python3
"""
Ingest Math .tex notes into Supabase.

Usage:
    python scripts/ingest_math_notes.py --class-level 9
    python scripts/ingest_math_notes.py --class-level 10

Expects .tex files at:
    Notes/Class {X}/Math/Content/Extracted/*.tex

Run scripts/extract_math_zips.py first to create those files.
"""
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import settings
from src.ingestion.math_pipeline import MathIngestionPipeline
from src.ingestion.subject_metadata import SUBJECT_METADATA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest Math notes into Supabase")
    parser.add_argument(
        "--class-level",
        type=int,
        required=True,
        choices=[9, 10],
        help="Class level to ingest",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing Math chunks before ingesting (clean slate)",
    )
    args = parser.parse_args()

    if not settings.supabase_url or not settings.supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent.parent
    tex_dir = base_dir / "Notes" / f"Class {args.class_level}" / "Math" / "Content" / "Extracted"

    if not tex_dir.exists():
        logger.error(f"Directory not found: {tex_dir}")
        logger.error("Run  python scripts/extract_math_zips.py  first.")
        sys.exit(1)

    chapter_metadata = SUBJECT_METADATA.get(args.class_level, {}).get("Math", {})

    pipeline = MathIngestionPipeline(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key,
        embedding_model=settings.embedding_model,
    )

    # Optional: clean existing Math data for this class
    if args.clean:
        logger.info(f"Cleaning existing Math chunks for Class {args.class_level}...")
        _clean_math_chunks(pipeline.loader, args.class_level)

    logger.info(f"\nIngesting Math Class {args.class_level} from {tex_dir}")
    results = pipeline.process_directory(
        directory=tex_dir,
        class_level=args.class_level,
        chapter_metadata=chapter_metadata,
    )

    logger.info("\n" + "=" * 60)
    logger.info("MATH INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Processed: {results['processed']} files")
    logger.info(f"Failed:    {results['failed']} files")
    logger.info(f"Total chunks: {results['total_chunks']}")

    for ch in results["chapters"]:
        logger.info(f"  {ch['file']}: {ch['chunks_loaded']} chunks")
        for err in ch.get("errors", []):
            logger.warning(f"    Error: {err}")


def _clean_math_chunks(loader, class_level: int):
    """Delete all Math chapter chunks for the given class level."""
    result = (
        loader.client.table("chapters")
        .select("id")
        .eq("class_level", class_level)
        .eq("subject", "Math")
        .execute()
    )
    for row in result.data:
        loader.clear_chapter_chunks(row["id"])
        loader.client.table("chapters").delete().eq("id", row["id"]).execute()
    logger.info(f"  Deleted {len(result.data)} chapter records")


if __name__ == "__main__":
    main()
