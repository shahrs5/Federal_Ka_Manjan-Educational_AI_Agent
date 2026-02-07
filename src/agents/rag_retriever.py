"""
RAG Retriever with chapter-scoped search.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import logging
import opik

from ..ingestion.embedding_generator import EmbeddingGenerator


logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved chunk with metadata."""

    text: str
    chapter_number: int
    chapter_title: str
    similarity: float
    metadata: Dict[str, Any]


class RAGRetriever:
    """
    Retrieve relevant chunks using vector similarity search.

    Supports:
    - Chapter-scoped search (filter by chapter)
    - Multi-chapter search
    - Metadata filtering
    """

    def __init__(
        self,
        supabase_client,
        embedding_generator: EmbeddingGenerator = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
        debug: bool = False,
    ):
        self.supabase = supabase_client
        self.embedder = embedding_generator or EmbeddingGenerator()
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.debug = debug

    @opik.track
    def retrieve(
        self,
        query: str,
        class_level: int,
        subject: str,
        chapter_numbers: List[int] = None,
        top_k: int = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.
        """
        top_k = top_k or self.top_k

        if self.debug:
            print(f"\n{'='*60}")
            print(f"[RETRIEVER] Query: {query}")
            print(f"[RETRIEVER] Searching chapters: {chapter_numbers or 'ALL'}")

        # Generate query embedding (use generate_query for better retrieval)
        if hasattr(self.embedder, 'generate_query'):
            query_embedding = self.embedder.generate_query(query)
        else:
            query_embedding = self.embedder.generate(query)

        if self.debug:
            print(f"[RETRIEVER] Embedding generated (dim={len(query_embedding)})")
            print(f"[RETRIEVER] First 5 values: {query_embedding[:5]}")

        # Execute vector search
        results = self._vector_search(
            query_embedding=query_embedding,
            class_level=class_level,
            subject=subject,
            chapter_numbers=chapter_numbers,
            top_k=top_k * 2,
        )

        if self.debug:
            print(f"[RETRIEVER] Raw results count: {len(results)}")
            for i, r in enumerate(results[:3]):
                print(f"  [{i}] similarity={r.get('similarity', 'N/A'):.3f}, "
                      f"chapter={r.get('chapter_number')}, "
                      f"text={r.get('chunk_text', '')[:80]}...")

        # Filter by similarity threshold
        filtered = [
            r
            for r in results
            if r.get("similarity", 0) >= self.similarity_threshold
        ]

        if self.debug:
            print(f"[RETRIEVER] After threshold filter ({self.similarity_threshold}): {len(filtered)} chunks")

        # Convert to RetrievedChunk objects
        chunks = []
        for r in filtered[:top_k]:
            chunks.append(
                RetrievedChunk(
                    text=r["chunk_text"],
                    chapter_number=r["chapter_number"],
                    chapter_title=r["chapter_title"],
                    similarity=r["similarity"],
                    metadata=r.get("metadata", {}),
                )
            )

        return chunks

    def _vector_search(
        self,
        query_embedding: List[float],
        class_level: int,
        subject: str,
        chapter_numbers: List[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Execute vector similarity search using Supabase RPC.
        """
        params = {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "filter_class": class_level,
            "filter_subject": subject,
        }

        if chapter_numbers:
            params["filter_chapters"] = chapter_numbers

        if self.debug:
            print(f"[RETRIEVER] Calling search_chunks RPC...")
            print(f"[RETRIEVER] Params: class={class_level}, subject={subject}, chapters={chapter_numbers}")

        try:
            result = self.supabase.rpc("search_chunks", params).execute()
            return result.data or []
        except Exception as e:
            if self.debug:
                print(f"[RETRIEVER] RPC Error: {e}")
            # Fallback: direct query without RPC
            return self._fallback_search(query_embedding, class_level, subject, chapter_numbers, top_k)

    def _fallback_search(
        self,
        query_embedding: List[float],
        class_level: int,
        subject: str,
        chapter_numbers: List[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fallback search using direct table query (no RPC).
        """
        if self.debug:
            print(f"[RETRIEVER] Using fallback search (direct query)...")

        # Get chapter IDs first
        query = self.supabase.table("chapters").select("id, chapter_number, chapter_title").eq(
            "class_level", class_level
        ).eq("subject", subject)

        if chapter_numbers:
            query = query.in_("chapter_number", chapter_numbers)

        chapters_result = query.execute()
        chapters = {c["id"]: c for c in chapters_result.data}

        if self.debug:
            print(f"[RETRIEVER] Found {len(chapters)} matching chapters")

        if not chapters:
            return []

        # Get chunks for these chapters
        chunks_result = self.supabase.table("document_chunks").select(
            "chunk_text, chapter_id, metadata"
        ).in_("chapter_id", list(chapters.keys())).limit(top_k * 5).execute()

        if self.debug:
            print(f"[RETRIEVER] Found {len(chunks_result.data)} chunks")

        # Manual similarity calculation (cosine)
        import numpy as np
        query_vec = np.array(query_embedding)

        results = []
        for chunk in chunks_result.data:
            chapter = chapters.get(chunk["chapter_id"], {})
            # For fallback, we can't calculate similarity without embeddings in response
            # Just return with similarity=0.5 as placeholder
            results.append({
                "chunk_text": chunk["chunk_text"],
                "chapter_number": chapter.get("chapter_number", 0),
                "chapter_title": chapter.get("chapter_title", "Unknown"),
                "similarity": 0.6,  # Placeholder
                "metadata": chunk.get("metadata", {}),
            })

        return results[:top_k]

    def retrieve_with_expansion(
        self,
        query: str,
        class_level: int,
        subject: str,
        chapter_numbers: List[int] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve with query expansion for better recall.
        """
        queries = [query]
        queries.extend(self._simple_expand(query))

        # Collect results from all queries
        all_chunks = []
        seen_texts = set()

        for q in queries:
            chunks = self.retrieve(
                query=q,
                class_level=class_level,
                subject=subject,
                chapter_numbers=chapter_numbers,
                top_k=self.top_k,
            )

            for chunk in chunks:
                # Deduplicate by text hash
                text_hash = hash(chunk.text[:100])
                if text_hash not in seen_texts:
                    seen_texts.add(text_hash)
                    all_chunks.append(chunk)

        # Sort by similarity and return top_k
        all_chunks.sort(key=lambda x: x.similarity, reverse=True)
        return all_chunks[: self.top_k]

    def _simple_expand(self, query: str) -> List[str]:
        """Simple query expansion without LLM."""
        expansions = []

        # Add "what is" prefix for definitions
        if not query.lower().startswith(
            ("what", "how", "why", "define", "explain")
        ):
            expansions.append(f"What is {query}")
            expansions.append(f"Explain {query}")

        return expansions
