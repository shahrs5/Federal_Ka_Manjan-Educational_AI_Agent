#!/usr/bin/env python3
"""
Test the RAG pipeline with sample questions.

Usage:
    python scripts/test_rag_pipeline.py

Requirements:
    - Run ingest_physics_notes.py first
    - Set GROQ_API_KEY in .env
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import settings
from src.services.groq_client import get_groq_client
from src.services.supabase_client import get_supabase_client
from src.ingestion.embedding_generator import EmbeddingGenerator
from src.agents.chapter_router import ChapterRouterAgent
from src.agents.rag_retriever import RAGRetriever
from src.agents.qa_agent import QAAgent


def main():
    """Test the RAG pipeline."""

    # Validate settings
    if not settings.groq_api_key:
        print("ERROR: GROQ_API_KEY must be set in .env")
        sys.exit(1)

    if not settings.supabase_url or not settings.supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    # Initialize clients
    groq_client = get_groq_client()
    supabase_client = get_supabase_client()
    embedder = EmbeddingGenerator(settings.embedding_model)

    # Enable debug mode
    DEBUG = True

    # Initialize agents
    router = ChapterRouterAgent(groq_client, model=settings.groq_model, debug=DEBUG)
    retriever = RAGRetriever(
        supabase_client=supabase_client,
        embedding_generator=embedder,
        top_k=settings.max_rag_results,
        similarity_threshold=settings.similarity_threshold,
        debug=DEBUG,
    )
    qa_agent = QAAgent(
        llm_client=groq_client,
        router=router,
        retriever=retriever,
        model=settings.groq_model,
    )

    # Test questions
    test_questions = [
        "What is Newton's second law of motion?",
        "Explain the concept of gravitational force.",
        "How does a vernier caliper work?",
        "What is the difference between heat and temperature?",
        "Define momentum and give its formula.",
    ]

    print("\n" + "=" * 70)
    print("RAG PIPELINE TEST")
    print("=" * 70)

    for i, question in enumerate(test_questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"Q: {question}\n")

        try:
            response = qa_agent.answer(
                query=question,
                class_level=9,
                subject="Physics",
            )

            print(f"Routed to: Chapter {response.chapter_used}")
            print(f"Confidence: {response.confidence:.2f}")
            print(f"\nAnswer:\n{response.answer}")

            if response.sources:
                print("\nSources:")
                for src in response.sources:
                    print(f"  - Chapter {src['chapter']}: {src['title']}")
                    print(f"    Relevance: {src['relevance']}")

        except Exception as e:
            print(f"Error: {e}")

        print("\n" + "-" * 70)


if __name__ == "__main__":
    main()
