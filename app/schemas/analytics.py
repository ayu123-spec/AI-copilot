"""Schemas for the analytics dashboard endpoint."""

from pydantic import BaseModel


class CountItem(BaseModel):
    label: str
    count: int


class TimePoint(BaseModel):
    date: str
    count: int


class AnalyticsSummary(BaseModel):
    total_queries: int
    avg_latency_ms: int | None = None
    conversations: int
    messages_total: int
    messages_user: int
    messages_assistant: int
    feedback_up: int
    feedback_down: int
    documents: int
    documents_ready: int
    chunks_total: int
    agent_runs: int
    by_type: list[CountItem]
    agent_mix: list[CountItem]
    query_type_mix: list[CountItem]
    activity: list[TimePoint]
