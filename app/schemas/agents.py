"""Schemas for the agent run, run-trace, and memory endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.memory import MemoryKind


class AgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    conversation_id: str | None = None  # continue/persist into this conversation
    agent: str | None = None  # force a specific agent; otherwise the router decides
    persist_history: bool = True


class CitationOut(BaseModel):
    index: int
    source: str
    page_number: int | None = None
    snippet: str


class AgentStepOut(BaseModel):
    thought: str | None = None
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    observation: str | None = None


class AgentRunResponse(BaseModel):
    run_id: str
    conversation_id: str | None = None
    agent: str
    answer: str
    citations: list[CitationOut]
    steps: list[AgentStepOut]
    metadata: dict[str, Any]


class AgentRunRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent: str
    query: str
    answer: str
    citations: list
    steps: list
    run_metadata: dict
    conversation_id: str | None
    created_at: datetime


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    kind: MemoryKind = MemoryKind.NOTE
    source: str | None = None


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: MemoryKind
    content: str
    source: str | None
    created_at: datetime


class MemoryRecallRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int | None = None


class RecalledMemoryOut(BaseModel):
    memory_id: str
    content: str
    kind: str
    score: float
