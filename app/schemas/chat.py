"""Schemas for the RAG chat endpoint, history, and feedback."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import MessageRole


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    conversation_id: str | None = None  # continue an existing conversation


class CitationOut(BaseModel):
    index: int
    source: str
    page_number: int | None = None
    snippet: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    citations: list[CitationOut]


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    title: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: MessageRole
    content: str
    citations: list
    feedback: str | None
    created_at: datetime


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
