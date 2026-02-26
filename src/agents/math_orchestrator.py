"""
Math Orchestrator — classifies intent then routes to the appropriate
Math sub-agent (MathFormulaAgent or MathSolvingAgent).
"""
import re
from typing import List, Dict, Any
import json

from .math_formula_agent import MathFormulaAgent
from .math_solving_agent import MathSolvingAgent
from .qa_agent import QAResponse


class MathOrchestrator:
    """
    Routes math queries between two sub-agents:

    1. **MathFormulaAgent** (RAG) — concept/formula lookups
    2. **MathSolvingAgent** (direct LLM) — problem-solving

    Classification strategy:
    - Heuristic first (fast, no API call) for obvious cases.
    - LLM fallback for ambiguous queries.
    """

    # Keywords that strongly indicate "solve this problem"
    SOLVE_KEYWORDS = [
        "solve", "calculate", "compute", "evaluate", "simplify",
        "factorise", "factorize", "factor", "expand", "find the value",
        "find x", "find y", "find the root", "find hcf", "find lcm",
        "determine", "verify", "prove that", "show that",
    ]

    # Regex patterns for equations / expressions to solve
    EQUATION_PATTERNS = [
        r"\d+\s*[xyz]\s*[\+\-\*/]\s*\d+\s*=",        # 2x + 5 = 10
        r"[xyz]\s*\^?\d*\s*[\+\-]\s*\d+\s*=",         # x^2 - 4 = 0
        r"solve\s*:?\s*",                               # "solve: ..."
        r"\d+\s*[\+\-\*/\^]\s*\d+",                    # numeric expression
    ]

    # Keywords that strongly indicate "explain concept / formula"
    CONCEPT_KEYWORDS = [
        "what is", "what are", "define", "definition",
        "explain", "describe", "formula for", "tell me about",
        "difference between", "how does", "why does",
        "meaning of", "state the",
    ]

    def __init__(
        self,
        formula_agent: MathFormulaAgent,
        solving_agent: MathSolvingAgent,
        llm_client=None,
        model_fast: str = "openai/gpt-oss-20b",
    ):
        self.formula_agent = formula_agent
        self.solving_agent = solving_agent
        self.llm = llm_client
        self.model_fast = model_fast

    def answer(
        self,
        query: str,
        class_level: int = 9,
        language: str = "en",
        history: List[Dict[str, str]] = None,
    ) -> QAResponse:
        intent = self._classify(query)

        if intent == "solve":
            response = self.solving_agent.answer(
                query=query,
                class_level=class_level,
                language=language,
                history=history,
            )
        else:
            response = self.formula_agent.answer(
                query=query,
                class_level=class_level,
                language=language,
                history=history,
            )

        # Attach math orchestration metadata for logging
        response.math_intent = intent
        response.agent_used = f"math_{intent}" if intent == "solve" else "math_formula"
        return response

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------

    def _classify(self, query: str) -> str:
        """Return 'solve' or 'concept'."""
        # 1. Heuristic first
        heuristic = self._heuristic_classify(query)
        if heuristic is not None:
            return heuristic

        # 2. LLM fallback
        if self.llm:
            return self._llm_classify(query)

        # 3. Default to concept (safer — uses RAG)
        return "concept"

    def _heuristic_classify(self, query: str) -> str | None:
        q = query.lower().strip()

        # Check concept keywords first (they tend to be unambiguous)
        for kw in self.CONCEPT_KEYWORDS:
            if kw in q:
                return "concept"

        # Check solve keywords
        for kw in self.SOLVE_KEYWORDS:
            if kw in q:
                return "solve"

        # Check equation patterns
        for pat in self.EQUATION_PATTERNS:
            if re.search(pat, q, re.IGNORECASE):
                return "solve"

        return None  # ambiguous

    def _llm_classify(self, query: str) -> str:
        try:
            resp = self.llm.chat.completions.create(
                model=self.model_fast,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the following math question as either "
                            "\"solve\" (needs step-by-step computation) or "
                            "\"concept\" (needs explanation/formula lookup). "
                            "Reply with a single word: solve or concept."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.0,
                max_tokens=8,
            )
            word = resp.choices[0].message.content.strip().lower()
            return "solve" if "solve" in word else "concept"
        except Exception:
            return "concept"
