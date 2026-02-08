"""
Math Formula / Concept Agent — RAG-based, for queries like
"what is the quadratic formula?" or "explain HCF and LCM".
"""
from typing import List, Dict, Any
import json

from .chapter_router import ChapterRouterAgent, RoutingResult
from .rag_retriever import RAGRetriever
from .qa_agent import QAResponse


class MathFormulaAgent:
    """
    RAG-based agent specialised for Math concepts and formulas.

    Same flow as QAAgent but with a Math-tutor system prompt that
    outputs LaTeX-formatted answers ($...$ inline, $$...$$ display,
    \\boxed{} for final answers).
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
        language: str = "en",
        history: List[Dict[str, str]] = None,
    ) -> QAResponse:
        history = history or []

        # 1. Rewrite query
        retrieval_query = self._rewrite_query(query, history)

        # 2. Route to chapters
        routing = self.router.route(
            query=retrieval_query,
            class_level=class_level,
            subject="Math",
        )

        # 3. Retrieve
        chapters_to_search = [routing.primary_chapter] + routing.secondary_chapters[:1]
        chunks = self.retriever.retrieve(
            query=retrieval_query,
            class_level=class_level,
            subject="Math",
            chapter_numbers=chapters_to_search,
            top_k=5,
        )

        # 4. Generate answer
        answer_result = self._generate_answer(
            query=query,
            chunks=chunks,
            class_level=class_level,
            language=language,
            history=history,
        )

        sources = [
            {
                "chapter": c.chapter_number,
                "title": c.chapter_title,
                "snippet": c.text[:200] + "..." if len(c.text) > 200 else c.text,
                "relevance": round(c.similarity, 3),
            }
            for c in chunks[:3]
        ]

        return QAResponse(
            answer=answer_result.get("answer", "I couldn't find an answer."),
            explanation=answer_result.get("explanation", ""),
            sources=sources,
            confidence=min(routing.confidence, answer_result.get("confidence", 0.8)),
            chapter_used=routing.primary_chapter,
            routing_info=routing,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rewrite_query(self, query: str, history: List[Dict[str, str]]) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a query rewriter for a Math tutoring system. "
                        "Rewrite the student's latest question so that it:\n"
                        "1. Fixes spelling and grammar\n"
                        "2. Resolves any references to the previous conversation "
                        "into a fully self-contained question\n"
                        "Return ONLY the rewritten question, nothing else."
                    ),
                }
            ]
            for msg in history[-4:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": query})

            resp = self.llm.chat.completions.create(
                model=self.model_fast,
                messages=messages,
                temperature=0.0,
                max_tokens=128,
            )
            rewritten = resp.choices[0].message.content.strip()
            return rewritten if rewritten else query
        except Exception:
            return query

    def _generate_answer(
        self,
        query: str,
        chunks,
        class_level: int,
        language: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        if not chunks and not history:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "explanation": "",
                "confidence": 0.3,
            }

        lang_instruction = ""
        if language == "ur":
            lang_instruction = "Respond in Urdu."
        elif language == "ur-roman":
            lang_instruction = "Respond in Roman Urdu (Urdu written in English letters)."

        system_prompt = (
            f"You are a Math tutor for Class {class_level} students in Pakistan (FBISE syllabus). "
            "Always respond with JSON. "
            "Use LaTeX notation for ALL math: $...$ for inline math, $$...$$ for display math. "
            "Use \\boxed{{}} to highlight final answers. "
            "Use the conversation history to maintain context. "
            "If reference material is provided, prefer it."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        if chunks:
            context = "\n\n---\n\n".join(
                f"[Chapter {c.chapter_number}: {c.chapter_title}]\n{c.text}"
                for c in chunks
            )
            user_prompt = (
                f"REFERENCE MATERIAL:\n{context}\n\n"
                f"STUDENT QUESTION: {query}\n\n"
                f"{lang_instruction}\n\n"
                f"Instructions:\n"
                f"1. Answer based on the reference material\n"
                f"2. Use simple language appropriate for Class {class_level}\n"
                f"3. Use LaTeX for ALL formulas\n"
                f"4. Keep the answer concise but complete\n"
            )
        else:
            user_prompt = (
                f"STUDENT QUESTION: {query}\n\n"
                f"{lang_instruction}\n\n"
                f"Instructions:\n"
                f"1. Answer using the conversation history above\n"
                f"2. Use simple language appropriate for Class {class_level}\n"
                f"3. Use LaTeX for ALL formulas\n"
                f"4. If you don't have enough context, say so\n"
            )

        user_prompt += (
            '\nRespond with ONLY valid JSON:\n'
            '{\n'
            '    "answer": "<your answer with LaTeX math>",\n'
            '    "explanation": "<optional additional explanation>",\n'
            '    "confidence": <0.0 to 1.0>,\n'
            '    "formulas_used": ["<formula1>", "<formula2>"]\n'
            '}'
        )

        messages.append({"role": "user", "content": user_prompt})

        resp = self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )

        return self._parse_json(resp.choices[0].message.content)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"answer": text, "explanation": "", "confidence": 0.5}
