#!/usr/bin/env python3
"""
Test network connectivity to diagnose the getaddrinfo error.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("NETWORK CONNECTIVITY TEST")
print("=" * 60)

# Test 1: Basic imports
print("\n[1/5] Testing basic imports...")
try:
    from src.config import settings
    print("✓ Config loaded")
    print(f"  Supabase URL: {settings.supabase_url}")
    print(f"  Embedding model: {settings.embedding_model}")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 2: Test Supabase connection
print("\n[2/5] Testing Supabase connection...")
try:
    from src.services.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    print("✓ Supabase client created")

    # Try a simple query
    result = supabase.table('chapters').select('id').limit(1).execute()
    print(f"✓ Supabase query successful ({len(result.data)} rows)")
except Exception as e:
    print(f"✗ Supabase connection failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

# Test 3: Test embedding model initialization
print("\n[3/5] Testing embedding model initialization...")
try:
    from src.ingestion.embedding_generator import EmbeddingGenerator
    embedder = EmbeddingGenerator(settings.embedding_model)
    print(f"✓ Embedding generator created (backend: {embedder.backend})")
    print(f"  Model: {embedder.model_name}")
    print(f"  Dimension: {embedder.dimension}")
except Exception as e:
    print(f"✗ Embedding initialization failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test DOCX extraction (no network needed)
print("\n[4/5] Testing DOCX extraction...")
try:
    from src.ingestion.docx_extractor import DocxExtractor
    extractor = DocxExtractor()

    # Find a test file
    test_file = Path("Notes/Class 9/Physics/Content/Chapter 1 - Notes (Final 1).docx")
    if test_file.exists():
        print(f"  Using test file: {test_file.name}")
        doc = extractor.extract(test_file)
        print(f"✓ DOCX extraction successful")
        print(f"  Sections: {len(doc.sections)}")
        print(f"  Words: {doc.metadata['word_count']}")
    else:
        print("  (Skipping - no test file found)")
except Exception as e:
    print(f"✗ DOCX extraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test embedding generation (may download model first time)
print("\n[5/5] Testing embedding generation...")
try:
    from src.ingestion.embedding_generator import EmbeddingGenerator
    embedder = EmbeddingGenerator(settings.embedding_model)

    test_text = "This is a test sentence for embedding generation."
    print("  Generating test embedding...")
    embedding = embedder.generate(test_text)
    print(f"✓ Embedding generated successfully")
    print(f"  Dimension: {len(embedding)}")
    print(f"  First 3 values: {embedding[:3]}")
except Exception as e:
    print(f"✗ Embedding generation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
