"""
LaTeX (.tex) extraction for Math notes.

Parses the custom LaTeX template used in Math notes (QuickBox, QAPair
environments) and returns the same ExtractedDocument / ExtractedSection
dataclasses used by DocxExtractor so downstream code stays identical.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .docx_extractor import ExtractedDocument, ExtractedSection


class LatexExtractor:
    """
    Parse .tex files produced by the Math notes template.

    Expected environments:
      \\begin{QuickBox} ... \\end{QuickBox}   -> formula summary section
      \\begin{QAPair}{Title} ... \\end{QAPair} -> one Q&A section each
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, file_path: Path) -> ExtractedDocument:
        raw = file_path.read_text(encoding="utf-8")

        chapter_num = self._extract_chapter_number(file_path.name)
        exercise_title = self._extract_exercise_title(raw, file_path.name)

        # Isolate document body
        body = self._get_body(raw)

        sections: List[ExtractedSection] = []

        # 1) QuickBox → formula summary
        for qb in self._extract_environments(body, "QuickBox"):
            cleaned = self._clean_latex(qb)
            if cleaned.strip():
                sections.append(
                    ExtractedSection(
                        title=f"Formula Summary - {exercise_title}",
                        content=cleaned,
                        level=1,
                        has_formula=True,
                        has_table=False,
                    )
                )

        # 2) QAPair → individual Q&A
        for title, content in self._extract_qapairs(body):
            cleaned = self._clean_latex(content)
            if cleaned.strip():
                sections.append(
                    ExtractedSection(
                        title=title,
                        content=cleaned,
                        level=2,
                        has_formula=self._has_math(cleaned),
                        has_table=False,
                    )
                )

        full_text = "\n\n".join(s.content for s in sections)

        return ExtractedDocument(
            filename=file_path.name,
            chapter_number=chapter_num,
            sections=sections,
            full_text=full_text,
            metadata={
                "total_sections": len(sections),
                "has_tables": False,
                "has_formulas": any(s.has_formula for s in sections),
                "word_count": len(full_text.split()),
                "exercise_title": exercise_title,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_body(raw: str) -> str:
        """Return text between \\begin{document} and \\end{document}."""
        m = re.search(
            r"\\begin\{document\}(.*?)\\end\{document\}",
            raw,
            re.DOTALL,
        )
        return m.group(1) if m else raw

    @staticmethod
    def _extract_chapter_number(filename: str) -> int:
        m = re.search(r"Chapter\s+(\d+)", filename, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _extract_exercise_title(raw: str, filename: str) -> str:
        """Derive exercise title from the filename (most reliable)."""
        # Try filename first: "Class 9 Math - Chapter 4 (Exercise 4.5).tex"
        m = re.search(r"\((.*?)\)", filename)
        if m:
            return m.group(1)

        # Fallback: try the \begin{center} heading
        m2 = re.search(
            r"\\begin\{center\}.*?\{(Exercise[^}]*)\}",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if m2:
            title = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", m2.group(1))
            title = re.sub(r"\\[a-zA-Z]+", "", title).strip().strip("{}")
            if title:
                return title

        return "Exercise"

    # ---- environment extraction ----

    @staticmethod
    def _extract_environments(body: str, env_name: str) -> List[str]:
        """Extract all occurrences of \\begin{env}...\\end{env}."""
        pattern = re.compile(
            rf"\\begin\{{{env_name}\}}(.*?)\\end\{{{env_name}\}}",
            re.DOTALL,
        )
        return [m.group(1) for m in pattern.finditer(body)]

    @staticmethod
    def _extract_qapairs(body: str) -> List[tuple]:
        """Return list of (title, content) for every QAPair."""
        pattern = re.compile(
            r"\\begin\{QAPair\}\{(.*?)\}(.*?)\\end\{QAPair\}",
            re.DOTALL,
        )
        return [(m.group(1).strip(), m.group(2).strip()) for m in pattern.finditer(body)]

    # ---- LaTeX cleaning ----

    def _clean_latex(self, text: str) -> str:
        """Strip decorative LaTeX while preserving math notation."""

        # Replace \tcblower with solution separator
        text = re.sub(r"\\tcblower", "\n--- SOLUTION ---\n", text)

        # Replace \Step{N} with readable text
        text = re.sub(r"\\Step\{(\d+)\}", r"Step \1:", text)

        # Remove tikzpicture environments
        text = re.sub(
            r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
            "[Diagram]",
            text,
            flags=re.DOTALL,
        )

        # Remove color/font commands (preserve their content)
        # Handle nested \textcolor{color}{content}
        text = re.sub(r"\\textcolor\{[^}]*\}\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\color\{[^}]*\}", "", text)
        text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\bfseries\b", "", text)
        text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)

        # Remove spacing commands
        text = re.sub(r"\\(?:par|medskip|bigskip|smallskip|noindent)\b", "", text)
        text = re.sub(r"\\\\\[[\d.]*pt\]", "\n", text)
        text = re.sub(r"\\\\", "\n", text)

        # Remove \begin{itemize/enumerate} ... \end{} but keep \item text
        text = re.sub(r"\\begin\{(?:itemize|enumerate)\}(?:\[[^\]]*\])?", "", text)
        text = re.sub(r"\\end\{(?:itemize|enumerate)\}", "", text)
        text = re.sub(r"\\item\b", "- ", text)

        # Remove stray braces left after command removal (e.g. {\bfseries text})
        # Only remove braces NOT preceded by a backslash (preserves \text{}, \boxed{}, etc.)
        text = re.sub(r"(?<!\\)(?<![a-zA-Z])\{([^{}$]*?)\}", r"\1", text)

        # Remove \begin{center}/\end{center}
        text = re.sub(r"\\begin\{center\}", "", text)
        text = re.sub(r"\\end\{center\}", "", text)

        # Remove font-size commands
        text = re.sub(r"\\(?:LARGE|Large|large|normalsize|small|footnotesize|tiny)\b", "", text)

        # Remove \href but keep text
        text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)

        # Remove remaining benign commands that have no argument
        text = re.sub(r"\\(?:hfill|vfill|clearpage|newpage|pagebreak)\b", "", text)

        # Remove stray % comments (but not inside math)
        text = re.sub(r"(?m)^%.*$", "", text)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    @staticmethod
    def _has_math(text: str) -> bool:
        """Check whether text contains LaTeX math notation."""
        return bool(
            re.search(r"\$.*?\$", text)
            or re.search(r"\\\[.*?\\\]", text, re.DOTALL)
            or re.search(r"\\frac\b|\\boxed\b|\\sqrt\b|\\begin\{aligned\}", text)
        )
