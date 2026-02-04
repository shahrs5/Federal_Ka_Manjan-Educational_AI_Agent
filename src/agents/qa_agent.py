"""
Question-Answering Agent using RAG context.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import json

from .chapter_router import ChapterRouterAgent, RoutingResult
from .rag_retriever import RAGRetriever, RetrievedChunk


@dataclass
class QAResponse:
    """Response from QA Agent."""

    answer: str
    explanation: str
    sources: List[Dict[str, Any]]
    confidence: float
    chapter_used: int
    routing_info: RoutingResult


class QAAgent:
    """
    Question-Answering Agent integrating routing and RAG.

    Flow:
    1. Route query to relevant chapters
    2. Retrieve relevant chunks
    3. Generate answer using LLM with RAG context
    """

    def __init__(
        self,
        llm_client,
        router: ChapterRouterAgent,
        retriever: RAGRetriever,
        model: str = "openai/gpt-oss-120b",
        model_fast: str = "openai/gpt-oss-20b",
    ):
        self.llm = llm_client
        self.router = router
        self.retriever = retriever
        self.model = model
        self.model_fast = model_fast

    def answer(
        self,
        query: str,
        class_level: int = 9,
        subject: str = "Physics",
        language: str = "en",
    ) -> QAResponse:
        """
        Answer a student's question using RAG.

        Args:
            query: Student's question
            class_level: Class level
            subject: Subject
            language: Response language (en, ur, ur-roman)

        Returns:
            QAResponse with answer and sources
        """
        # Step 1: Rewrite query for better retrieval
        retrieval_query = self._rewrite_query(query, subject)

        # Step 2: Route to relevant chapters (using rewritten query)
        routing = self.router.route(
            query=retrieval_query,
            class_level=class_level,
            subject=subject,
        )

        # Step 3: Retrieve relevant chunks (using rewritten query)
        chapters_to_search = [routing.primary_chapter] + routing.secondary_chapters[:1]

        chunks = self.retriever.retrieve(
            query=retrieval_query,
            class_level=class_level,
            subject=subject,
            chapter_numbers=chapters_to_search,
            top_k=5,
        )

        # Step 4: Generate answer with RAG context (using ORIGINAL query)
        answer_result = self._generate_answer(
            query=query,
            chunks=chunks,
            class_level=class_level,
            language=language,
        )

        # Build sources
        sources = [
            {
                "chapter": chunk.chapter_number,
                "title": chunk.chapter_title,
                "snippet": chunk.text[:200] + "..."
                if len(chunk.text) > 200
                else chunk.text,
                "relevance": round(chunk.similarity, 3),
            }
            for chunk in chunks[:3]
        ]

        return QAResponse(
            answer=answer_result.get("answer", "I couldn't find an answer."),
            explanation=answer_result.get("explanation", ""),
            sources=sources,
            confidence=min(
                routing.confidence, answer_result.get("confidence", 0.8)
            ),
            chapter_used=routing.primary_chapter,
            routing_info=routing,
        )

    def _rewrite_query(self, query: str, subject: str) -> str:
        """
        Rewrite student query to fix spelling/grammar and make it clearer
        for better RAG retrieval. Falls back to original query on any error.
        """
        try:
            response = self.llm.chat.completions.create(
                model=self.model_fast,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a query rewriter for a {subject} tutoring system. "
                            "Rewrite the student's question to fix spelling, grammar, and clarity. "
                            "Keep the meaning the same. Return ONLY the rewritten question, nothing else."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.0,
                max_tokens=128,
            )
            rewritten = response.choices[0].message.content.strip()
            return rewritten if rewritten else query
        except Exception:
            return query

    def _generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        class_level: int,
        language: str,
    ) -> Dict[str, Any]:
        """Generate answer using LLM with RAG context."""

        if not chunks:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "explanation": "",
                "confidence": 0.3,
            }

        # Build context from chunks
        context = "\n\n---\n\n".join(
            [
                f"[Chapter {c.chapter_number}: {c.chapter_title}]\n{c.text}"
                for c in chunks
            ]
        )

        language_instruction = ""
        if language == "ur":
            language_instruction = "Respond in Urdu."
        elif language == "ur-roman":
            language_instruction = (
                "Respond in Roman Urdu (Urdu written in English letters)."
            )

        prompt = f"""You are a helpful tutor for Class {class_level} Physics students.

REFERENCE MATERIAL:
{context}

STUDENT QUESTION: {query}

{language_instruction}

Instructions:
1. Answer based ONLY on the reference material provided
2. Use simple language appropriate for Class {class_level}
3. If the answer requires formulas, show them clearly
4. If the reference material doesn't fully answer the question, say so
5. Keep the answer concise but complete (2-3 paragraphs max)

Respond with ONLY valid JSON:
{{
    "answer": "<your answer>",
    "explanation": "<optional additional explanation>",
    "confidence": <0.0 to 1.0 based on how well the reference material answers the question>,
    "formulas_used": ["<formula1>", "<formula2>"]
}}"""

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a physics tutor. Always respond with JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1000,
        )

        return self._parse_json(response.choices[0].message.content)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback: return the text as-is
            return {
                "answer": text,
                "explanation": "",
                "confidence": 0.5,
            }
