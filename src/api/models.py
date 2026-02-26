"""Pydantic models for API request/response."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ChatHistoryMessage(BaseModel):
    """A single message in the chat history."""

    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    query: str = Field(..., min_length=1, description="The student's question")
    class_level: int = Field(default=9, ge=9, le=10, description="Class level (9 or 10)")
    subject: str = Field(default="Physics", description="Subject name")
    language: str = Field(default="en", description="Response language: en, ur, ur-roman")
    history: List[ChatHistoryMessage] = Field(default=[], description="Previous messages in this session (max 10)")


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
    chapter_used: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str


# Auth models

class LoginRequest(BaseModel):
    """Request to set auth cookies after Supabase client-side login."""

    access_token: str
    refresh_token: str
    remember_me: bool = False


class SetPasswordRequest(BaseModel):
    """Set password for first-time login."""

    password: str = Field(..., min_length=6)


class FirstTimeCheckRequest(BaseModel):
    """Check if an email is a valid first-time user."""

    email: str = Field(..., min_length=3)


class FirstTimeSetPasswordRequest(BaseModel):
    """Set password for a first-time user (public, no auth required)."""

    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class InviteUserRequest(BaseModel):
    """Invite a single user by email."""

    email: str = Field(..., min_length=3)


class BulkInviteRequest(BaseModel):
    """Invite multiple users by comma-separated emails."""

    emails: str = Field(..., min_length=3)


class DeleteUserRequest(BaseModel):
    """Delete a user by ID."""

    user_id: str


class UserInfo(BaseModel):
    """User info returned by admin endpoints."""

    id: str
    email: str
    created_at: str
    last_sign_in: Optional[str] = None
    role: Optional[str] = None
