"""
Math Solving Agent — direct LLM call for solving math problems.

Used for queries like "solve 2x + 5 = 10" where no RAG is needed.
Optionally accepts retrieved context so it can reference similar
exercises from notes.
"""
from typing import List, Dict, Any, Optional
import json
import re

from .chapter_router import RoutingResult
from .qa_agent import QAResponse


class MathSolvingAgent:
    """
    Step-by-step math problem solver.

    - Direct LLM call (no RAG by default).
    - When *rag_context* is supplied, the LLM is told to mirror the
      style of the retrieved examples.
    """

    def __init__(
        self,
        llm_client,
        model: str = "openai/gpt-oss-120b",
    ):
        self.llm = llm_client
        self.model = model

    def answer(
        self,
        query: str,
        class_level: int = 9,
        language: str = "en",
        history: List[Dict[str, str]] = None,
        rag_context: Optional[str] = None,
    ) -> QAResponse:
        history = history or []
        result = self._solve(query, class_level, language, history, rag_context)

        return QAResponse(
            answer=result.get("answer", "I couldn't solve this problem."),
            explanation=result.get("explanation", ""),
            formulas=result.get("formulas", []),
            sources=[],
            confidence=result.get("confidence", 0.85),
            chapter_used=None,
            routing_info=RoutingResult(
                primary_chapter=0,
                secondary_chapters=[],
                confidence=result.get("confidence", 0.85),
                reasoning="Direct math problem solving — no chapter routing needed.",
                topics_identified=[],
            ),
            revised_query=query,
        )

    # ------------------------------------------------------------------

    def _solve(
        self,
        query: str,
        class_level: int,
        language: str,
        history: List[Dict[str, str]],
        rag_context: Optional[str],
    ) -> Dict[str, Any]:
        lang_instruction = ""
        if language == "ur":
            lang_instruction = "Write all explanatory text in Urdu, but keep math notation in LaTeX."
        elif language == "ur-roman":
            lang_instruction = "Write all explanatory text in Roman Urdu, but keep math notation in LaTeX."

        system_prompt = (
            f"You are a Math tutor for Class {class_level} students (FBISE syllabus). "
            "Solve the given problem step by step.\n\n"
            "Rules:\n"
            "- Number every step (Step 1, Step 2, ...)\n"
            "- Use LaTeX for ALL math: $...$ inline, $$...$$ display\n"
            "- Wrap the final answer in \\boxed{{}}\n"
            "- Keep explanations simple for a Class " + str(class_level) + " student\n"
            "- Always respond with valid JSON\n"
        )

        messages = [{"role": "system", "content": system_prompt}]

        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        user_prompt = ""
        if rag_context:
            user_prompt += (
                "Here are similar solved examples from the student's textbook for reference:\n"
                f"{rag_context}\n\n"
                "Now solve the following problem in a similar style:\n\n"
            )

        user_prompt += f"PROBLEM: {query}\n\n{lang_instruction}\n\n"
        user_prompt += (
            'Respond with ONLY valid JSON. IMPORTANT: escape ALL backslashes as \\\\ in JSON strings.\n'
            '{\n'
            '    "answer": "<step-by-step solution with LaTeX>",\n'
            '    "explanation": "<brief summary of the approach>",\n'
            '    "formulas": ["<key formula or law used, e.g. F = ma>"],\n'
            '    "confidence": <0.0 to 1.0>\n'
            '}'
        )

        messages.append({"role": "user", "content": user_prompt})

        resp = self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
        )

        return self._parse_json(resp.choices[0].message.content)

    @staticmethod
    def _sanitize_json_strings(text: str) -> str:
        """
        Walk the raw LLM output character-by-character and fix two common issues
        that occur inside JSON string values:
          1. Literal newlines / tabs  → proper JSON escapes (\\n, \\t)
          2. Bare LaTeX backslashes   → doubled (\\\\)
        Leaves the surrounding JSON structure (braces, colons, commas) untouched.
        """
        result = []
        in_string = False
        i = 0
        while i < len(text):
            c = text[i]
            if in_string:
                if c == '\\':
                    nxt = text[i + 1] if i + 1 < len(text) else ''
                    if nxt in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'):
                        # Already a valid JSON escape — keep both chars
                        result.append(c)
                        result.append(nxt)
                        i += 2
                    else:
                        # Invalid escape (LaTeX \circ, \boxed, etc.) — double the backslash
                        result.append('\\\\')
                        i += 1
                elif c == '"':
                    in_string = False
                    result.append(c)
                    i += 1
                elif c == '\n':
                    result.append('\\n')
                    i += 1
                elif c == '\r':
                    i += 1  # strip bare CR
                elif c == '\t':
                    result.append('\\t')
                    i += 1
                else:
                    result.append(c)
                    i += 1
            else:
                if c == '"':
                    in_string = True
                result.append(c)
                i += 1
        return ''.join(result)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            text = text.strip()
            # Pass 1: direct parse (works when LLM output is clean)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            # Pass 2: sanitize inside strings, then parse
            return json.loads(MathSolvingAgent._sanitize_json_strings(text))
        except Exception:
            return {"answer": text, "explanation": "", "formulas": [], "confidence": 0.5}
