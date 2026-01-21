"""
Text chunking strategies optimized for educational content.
"""
from dataclasses import dataclass
from typing import List
import re

from .docx_extractor import ExtractedSection


@dataclass
class Chunk:
    """Represents a text chunk for embedding."""

    text: str
    chunk_index: int
    metadata: dict


class TextChunker:
    """
    Chunk text for RAG with educational content optimization.

    Strategy:
    1. Prefer semantic boundaries (sections, paragraphs)
    2. Keep formulas and definitions intact
    3. Add overlap for context continuity
    4. Target ~300-500 words per chunk
    """

    def __init__(
        self,
        chunk_size: int = 500,  # Target words per chunk
        chunk_overlap: int = 50,  # Overlap words
        min_chunk_size: int = 100,  # Minimum words
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        sections: List[ExtractedSection],
        chapter_title: str,
    ) -> List[Chunk]:
        """
        Chunk document sections into RAG-ready chunks.

        Args:
            sections: List of ExtractedSection from DocxExtractor
            chapter_title: Title of the chapter for context

        Returns:
            List of Chunk objects
        """
        # First, try chunking each section individually
        chunks = []
        chunk_index = 0

        for section in sections:
            section_chunks = self._chunk_section(
                section_title=section.title,
                content=section.content,
                chapter_title=chapter_title,
                has_formula=section.has_formula,
                has_table=section.has_table,
                start_index=chunk_index,
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        # If no chunks were created (all sections too small), combine all content
        if not chunks and sections:
            combined_content = "\n\n".join(
                f"{s.title}\n{s.content}" if s.title != "Introduction" else s.content
                for s in sections
                if s.content.strip()
            )
            has_formula = any(s.has_formula for s in sections)
            has_table = any(s.has_table for s in sections)

            # Chunk the combined content with lower minimum
            chunks = self._chunk_combined_content(
                content=combined_content,
                chapter_title=chapter_title,
                has_formula=has_formula,
                has_table=has_table,
            )

        return chunks

    def _chunk_combined_content(
        self,
        content: str,
        chapter_title: str,
        has_formula: bool,
        has_table: bool,
    ) -> List[Chunk]:
        """Chunk combined content with a lower minimum threshold."""
        if not content.strip():
            return []

        paragraphs = self._split_paragraphs(content)
        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            para_words = len(para.split())

            if current_word_count + para_words > self.chunk_size and current_chunk:
                chunks.append(
                    self._create_chunk(
                        text="\n\n".join(current_chunk),
                        index=len(chunks),
                        section_title="Combined",
                        chapter_title=chapter_title,
                        has_formula=has_formula,
                        has_table=has_table,
                    )
                )
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_word_count = len(overlap_text.split()) if overlap_text else 0

            current_chunk.append(para)
            current_word_count += para_words

        # Save final chunk with lower minimum (50 words instead of 100)
        if current_chunk and current_word_count >= 50:
            chunks.append(
                self._create_chunk(
                    text="\n\n".join(current_chunk),
                    index=len(chunks),
                    section_title="Combined",
                    chapter_title=chapter_title,
                    has_formula=has_formula,
                    has_table=has_table,
                )
            )
        elif current_chunk and chunks:
            prev_chunk = chunks[-1]
            prev_chunk.text += "\n\n" + "\n\n".join(current_chunk)

        return chunks

    def _chunk_section(
        self,
        section_title: str,
        content: str,
        chapter_title: str,
        has_formula: bool,
        has_table: bool,
        start_index: int,
    ) -> List[Chunk]:
        """Chunk a single section."""

        if not content.strip():
            return []

        # Split into paragraphs first
        paragraphs = self._split_paragraphs(content)

        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            para_words = len(para.split())

            # If single paragraph is too large, split it
            if para_words > self.chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunks.append(
                        self._create_chunk(
                            text="\n\n".join(current_chunk),
                            index=start_index + len(chunks),
                            section_title=section_title,
                            chapter_title=chapter_title,
                            has_formula=has_formula,
                            has_table=has_table,
                        )
                    )
                    current_chunk = []
                    current_word_count = 0

                # Split large paragraph by sentences
                sentence_chunks = self._split_by_sentences(para)
                for sent_chunk in sentence_chunks:
                    chunks.append(
                        self._create_chunk(
                            text=sent_chunk,
                            index=start_index + len(chunks),
                            section_title=section_title,
                            chapter_title=chapter_title,
                            has_formula=has_formula,
                            has_table=has_table,
                        )
                    )
                continue

            # Check if adding this paragraph exceeds chunk size
            if (
                current_word_count + para_words > self.chunk_size
                and current_chunk
            ):
                # Save current chunk
                chunks.append(
                    self._create_chunk(
                        text="\n\n".join(current_chunk),
                        index=start_index + len(chunks),
                        section_title=section_title,
                        chapter_title=chapter_title,
                        has_formula=has_formula,
                        has_table=has_table,
                    )
                )

                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_word_count = (
                    len(overlap_text.split()) if overlap_text else 0
                )

            current_chunk.append(para)
            current_word_count += para_words

        # Don't forget the last chunk
        if current_chunk and current_word_count >= self.min_chunk_size:
            chunks.append(
                self._create_chunk(
                    text="\n\n".join(current_chunk),
                    index=start_index + len(chunks),
                    section_title=section_title,
                    chapter_title=chapter_title,
                    has_formula=has_formula,
                    has_table=has_table,
                )
            )
        elif current_chunk and chunks:
            # Append to previous chunk if too small
            prev_chunk = chunks[-1]
            prev_chunk.text += "\n\n" + "\n\n".join(current_chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split large text by sentences into chunk-sized pieces."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current = []
        current_words = 0

        for sent in sentences:
            sent_words = len(sent.split())
            if current_words + sent_words > self.chunk_size and current:
                chunks.append(" ".join(current))
                current = []
                current_words = 0
            current.append(sent)
            current_words += sent_words

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _get_overlap(self, chunk_parts: List[str]) -> str:
        """Get overlap text from end of chunk."""
        if not chunk_parts:
            return ""

        # Take last part or portion of it
        last_part = chunk_parts[-1]
        words = last_part.split()

        if len(words) <= self.chunk_overlap:
            return last_part

        return " ".join(words[-self.chunk_overlap :])

    def _create_chunk(
        self,
        text: str,
        index: int,
        section_title: str,
        chapter_title: str,
        has_formula: bool,
        has_table: bool,
    ) -> Chunk:
        """Create a Chunk object with metadata."""

        # Detect content type
        content_type = self._detect_content_type(text)

        return Chunk(
            text=text,
            chunk_index=index,
            metadata={
                "section_title": section_title,
                "chapter_title": chapter_title,
                "content_type": content_type,
                "has_formula": has_formula or self._has_formula(text),
                "has_table": has_table,
                "word_count": len(text.split()),
            },
        )

    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content in the chunk."""
        text_lower = text.lower()

        if re.search(r"definition|is defined as|refers to", text_lower):
            return "definition"
        elif re.search(
            r"example|for instance|consider|suppose|let us", text_lower
        ):
            return "example"
        elif re.search(r"formula|equation|[A-Za-z]\s*=\s*[A-Za-z]", text):
            return "formula"
        elif re.search(
            r"exercise|question|problem|solve|calculate|find", text_lower
        ):
            return "exercise"
        else:
            return "explanation"

    def _has_formula(self, text: str) -> bool:
        """Check if text contains formulas."""
        formula_patterns = [
            r"[A-Za-z]\s*=\s*[A-Za-z0-9\*/\+\-\^]+",
        ]
        return any(re.search(p, text) for p in formula_patterns)
