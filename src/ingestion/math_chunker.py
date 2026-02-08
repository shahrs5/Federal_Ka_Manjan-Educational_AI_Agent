"""
Math-specific chunking that respects the QuickBox / QAPair structure.

Unlike the generic TextChunker, this module treats each logical unit
(formula summary or Q&A pair) as an atomic chunk so mathematical
context is never broken across boundaries.
"""
import re
from typing import List

from .docx_extractor import ExtractedSection
from .text_chunker import Chunk


class MathChunker:
    """
    Chunk Math ExtractedSections with structure awareness.

    Rules:
    - Formula Summary (QuickBox)  -> always ONE chunk, never split.
    - Each QAPair                 -> ONE chunk (question + solution).
      If the pair exceeds *max_words* it is split at the
      ``--- SOLUTION ---`` marker into two chunks.
    - Every chunk is prefixed with structured context for better
      embedding quality.
    """

    def __init__(self, max_words: int = 800):
        self.max_words = max_words

    def chunk_document(
        self,
        sections: List[ExtractedSection],
        chapter_title: str,
        class_level: int = 9,
        exercise_title: str = "",
    ) -> List[Chunk]:
        chunks: List[Chunk] = []
        idx = 0

        prefix = f"Class {class_level} Math, {chapter_title}"
        if exercise_title:
            prefix += f" ({exercise_title})"

        for section in sections:
            is_formula = section.title.startswith("Formula Summary")
            content_type = "formula_summary" if is_formula else "question_answer"
            word_count = len(section.content.split())
            has_diagram = "[Diagram]" in section.content

            # Build the chunk text with context prefix
            chunk_header = f"{prefix} - {section.title}"
            full_text = f"{chunk_header}\n\n{section.content}"

            if word_count <= self.max_words or is_formula:
                # Single chunk
                chunks.append(
                    Chunk(
                        text=full_text,
                        chunk_index=idx,
                        metadata={
                            "section_title": section.title,
                            "chapter_title": chapter_title,
                            "exercise_title": exercise_title,
                            "content_type": content_type,
                            "has_formula": section.has_formula,
                            "has_table": False,
                            "has_diagram": has_diagram,
                            "word_count": len(full_text.split()),
                        },
                    )
                )
                idx += 1
            else:
                # Split at solution separator
                parts = section.content.split("--- SOLUTION ---", 1)
                if len(parts) == 2:
                    q_text = f"{chunk_header} [Question]\n\n{parts[0].strip()}"
                    s_text = f"{chunk_header} [Solution]\n\n{parts[1].strip()}"

                    chunks.append(
                        Chunk(
                            text=q_text,
                            chunk_index=idx,
                            metadata={
                                "section_title": section.title,
                                "chapter_title": chapter_title,
                                "exercise_title": exercise_title,
                                "content_type": "question",
                                "has_formula": section.has_formula,
                                "has_table": False,
                                "has_diagram": has_diagram,
                                "word_count": len(q_text.split()),
                            },
                        )
                    )
                    idx += 1

                    chunks.append(
                        Chunk(
                            text=s_text,
                            chunk_index=idx,
                            metadata={
                                "section_title": section.title,
                                "chapter_title": chapter_title,
                                "exercise_title": exercise_title,
                                "content_type": "solution",
                                "has_formula": section.has_formula,
                                "has_table": False,
                                "has_diagram": has_diagram,
                                "word_count": len(s_text.split()),
                            },
                        )
                    )
                    idx += 1
                else:
                    # No separator found — keep as one chunk
                    chunks.append(
                        Chunk(
                            text=full_text,
                            chunk_index=idx,
                            metadata={
                                "section_title": section.title,
                                "chapter_title": chapter_title,
                                "exercise_title": exercise_title,
                                "content_type": content_type,
                                "has_formula": section.has_formula,
                                "has_table": False,
                                "has_diagram": has_diagram,
                                "word_count": len(full_text.split()),
                            },
                        )
                    )
                    idx += 1

        return chunks
