"""Schemas for the RAG chat endpoint."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)


class CitationOut(BaseModel):
    index: int
    source: str
    page_number: int | None = None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
