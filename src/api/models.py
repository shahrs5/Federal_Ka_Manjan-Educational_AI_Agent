"""Pydantic models for API request/response."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    query: str = Field(..., min_length=1, description="The student's question")
    class_level: int = Field(default=9, ge=9, le=10, description="Class level (9 or 10)")
    subject: str = Field(default="Physics", description="Subject name")
    language: str = Field(default="en", description="Response language: en, ur, ur-roman")


class SourceInfo(BaseModel):
    """Source information for citations."""

    chapter: int
    title: str
    snippet: str
    relevance: float


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str
    explanation: Optional[str] = ""
    sources: List[SourceInfo]
    confidence: float
    chapter_used: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str
