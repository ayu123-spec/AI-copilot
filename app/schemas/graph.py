"""Schemas for the knowledge-graph endpoints."""

from pydantic import BaseModel, Field


class GraphBuildRequest(BaseModel):
    # If omitted, the graph is built from the workspace's ingested document chunks.
    texts: list[str] | None = None


class GraphBuildResponse(BaseModel):
    entities: int
    relationships: int


class EntityOut(BaseModel):
    id: str
    name: str
    type: str


class GraphFactOut(BaseModel):
    source: str
    relation: str
    target: str


class GraphQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    depth: int | None = None


class GraphQueryResponse(BaseModel):
    entities: list[EntityOut]
    facts: list[GraphFactOut]
