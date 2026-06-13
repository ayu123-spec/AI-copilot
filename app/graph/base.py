"""Knowledge-graph core types and the storage interface.

Entities and relationships are tenant-scoped: every node and edge carries an
organization and workspace id, and all reads filter on them, so one tenant's
graph is never visible to another. A :class:`GraphStore` has two
implementations — an in-process store (default, offline, used by tests) and a
Neo4j-backed store for production — sharing this interface so the rest of the
system stays backend-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


def normalize_name(name: str) -> str:
    """Collapse whitespace; used so the same entity merges across extractions."""
    return " ".join(name.split()).strip()


def entity_id(workspace_id: str, type_: str, name: str) -> str:
    """Deterministic id: same (workspace, type, name) always maps to one node."""
    return f"{workspace_id}:{type_.lower()}:{normalize_name(name).lower()}"


@dataclass
class Entity:
    """An extracted entity: a Person, Company, Project, Department, etc."""

    name: str
    type: str = "Entity"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """A directed edge between two entities (e.g. ``WORKS_FOR``)."""

    source: str
    target: str
    type: str
    source_type: str = "Entity"
    target_type: str = "Entity"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StoredEntity:
    """An entity as held in the store, with its deterministic id."""

    id: str
    name: str
    type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphFact:
    """A traversed relationship, ready to render as a fact for the LLM."""

    source: str
    relation: str
    target: str

    def as_text(self) -> str:
        return f"{self.source} —{self.relation}→ {self.target}"


class GraphStore(ABC):
    """Backend-agnostic tenant-scoped knowledge-graph storage."""

    @abstractmethod
    def add_entities(
        self, entities: list[Entity], *, organization_id: str, workspace_id: str
    ) -> int:
        """Upsert entities; return the number written."""

    @abstractmethod
    def add_relationships(
        self,
        relationships: list[Relationship],
        *,
        organization_id: str,
        workspace_id: str,
    ) -> int:
        """Upsert relationships (creating any missing endpoint entities)."""

    @abstractmethod
    def get_entity(
        self,
        name: str,
        *,
        organization_id: str,
        workspace_id: str,
        type: str | None = None,
    ) -> StoredEntity | None:
        """Look up an entity by name (case-insensitive), optionally by type."""

    @abstractmethod
    def search_entities(
        self,
        text: str,
        *,
        organization_id: str,
        workspace_id: str,
        limit: int = 10,
    ) -> list[StoredEntity]:
        """Find entities whose name contains ``text`` (case-insensitive)."""

    @abstractmethod
    def neighbors(
        self,
        entity_id: str,
        *,
        organization_id: str,
        workspace_id: str,
        depth: int = 1,
    ) -> list[GraphFact]:
        """Relationships reachable from an entity within ``depth`` hops."""

    @abstractmethod
    def clear(self, *, organization_id: str, workspace_id: str) -> None:
        """Remove all of a workspace's entities and relationships."""
