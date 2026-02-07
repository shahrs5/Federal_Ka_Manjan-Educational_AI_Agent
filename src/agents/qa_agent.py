"""
Question-Answering Agent using RAG context.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import json
from .chapter_router import ChapterRouterAgent, RoutingResult
from .rag_retriever import RAGRetriever, RetrievedChunk
import opik


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

    @opik.track
    def answer(
        self,
        query: str,
        class_level: int = 9,
        subject: str = "Physics",
        language: str = "en",
        history: List[Dict[str, str]] = None,
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
        # Step 1: Rewrite query for better retrieval (needs history to resolve follow-ups)
        retrieval_query = self._rewrite_query(query, subject, history or [])

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
            history=history or [],
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

    @opik.track
    def _rewrite_query(self, query: str, subject: str, history: List[Dict[str, str]]) -> str:
        """
        Rewrite student query to fix spelling/grammar and resolve any references
        to previous messages so it becomes a self-contained retrieval query.
        Falls back to original query on any error.
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a query rewriter for a {subject} tutoring system. "
                        "Rewrite the student's latest question so that it:\n"
                        "1. Fixes spelling and grammar\n"
                        "2. Resolves any references to the previous conversation (e.g. 'explain it', 'what about that') into a fully self-contained question\n"
                        "Return ONLY the rewritten question, nothing else."
                    ),
                },
            ]

            # Include last 4 history messages (2 turns) for context — keeps token usage low
            for msg in history[-4:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": query})

            response = self.llm.chat.completions.create(
                model=self.model_fast,
                messages=messages,
                temperature=0.0,
                max_tokens=128,
            )
            rewritten = response.choices[0].message.content.strip()
            return rewritten if rewritten else query
        except Exception:
            return query

    @opik.track
    def _generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        class_level: int,
        language: str,
        history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate answer using LLM with RAG context and chat history."""

        # Hard bail only if we have nothing at all — no chunks AND no history
        if not chunks and not history:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "explanation": "",
                "confidence": 0.3,
            }

        language_instruction = ""
        if language == "ur":
            language_instruction = "Respond in Urdu."
        elif language == "ur-roman":
            language_instruction = (
                "Respond in Roman Urdu (Urdu written in English letters)."
            )

        system_prompt = (
            f"You are a helpful tutor for Class {class_level} students. "
            "Always respond with JSON. "
            "Use the conversation history to maintain context. "
            "If reference material is provided, prefer it. "
            "If no reference material is available but the conversation history covers the topic, answer from that."
        )

        messages = [{"role": "system", "content": system_prompt}]

        for msg in (history or []):
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Build the current-turn prompt — include RAG context only if we actually have chunks
        if chunks:
            context = "\n\n---\n\n".join(
                [
                    f"[Chapter {c.chapter_number}: {c.chapter_title}]\n{c.text}"
                    for c in chunks
                ]
            )
            current_prompt = f"""REFERENCE MATERIAL:
{context}

STUDENT QUESTION: {query}

{language_instruction}

Instructions:
1. Answer based on the reference material provided
2. Use simple language appropriate for Class {class_level}
3. If the answer requires formulas, show them clearly
4. Keep the answer concise but complete (2-3 paragraphs max)
5. If the student is following up on something from the conversation, use that context too"""
        else:
            current_prompt = f"""STUDENT QUESTION: {query}

{language_instruction}

Instructions:
1. No new reference material was retrieved — answer using the conversation history above
2. Use simple language appropriate for Class {class_level}
3. If the answer requires formulas, show them clearly
4. If you don't have enough context to answer, say so
5. Keep the answer concise but complete (2-3 paragraphs max)"""

        current_prompt += f"""

Respond with ONLY valid JSON:
{{
    "answer": "<your answer>",
    "explanation": "<optional additional explanation>",
    "confidence": <0.0 to 1.0>,
    "formulas_used": ["<formula1>", "<formula2>"]
}}"""

        messages.append({"role": "user", "content": current_prompt})

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
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
