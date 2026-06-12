"""Pydantic schemas for documents and search."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    filename: str
    content_type: str
    status: DocumentStatus
    num_chunks: int
    error: str | None = None
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)


class SearchResultOut(BaseModel):
    score: float
    text: str
    document_id: str | None = None
    page_number: int | None = None
    source: str | None = None
