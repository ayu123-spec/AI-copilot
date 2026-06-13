"""In-process knowledge-graph store.

The default backend: holds the graph in plain dictionaries keyed by tenant.
Fully offline and deterministic, so it powers tests and local development with
no Neo4j server. Multi-hop traversal is a breadth-first walk over an undirected
view of the edges, but each returned :class:`GraphFact` preserves the edge's
stored direction.
"""

from collections import deque

from app.graph.base import (
    Entity,
    GraphFact,
    GraphStore,
    Relationship,
    StoredEntity,
    entity_id,
    normalize_name,
)


class InMemoryGraphStore(GraphStore):
    def __init__(self) -> None:
        # (org, ws) -> {entity_id: StoredEntity}
        self._entities: dict[tuple[str, str], dict[str, StoredEntity]] = {}
        # (org, ws) -> list[(source_id, relation, target_id)]
        self._edges: dict[tuple[str, str], list[tuple[str, str, str]]] = {}

    def _ents(self, org: str, ws: str) -> dict[str, StoredEntity]:
        return self._entities.setdefault((org, ws), {})

    def _rels(self, org: str, ws: str) -> list[tuple[str, str, str]]:
        return self._edges.setdefault((org, ws), [])

    def add_entities(
        self, entities: list[Entity], *, organization_id: str, workspace_id: str
    ) -> int:
        store = self._ents(organization_id, workspace_id)
        for ent in entities:
            eid = entity_id(workspace_id, ent.type, ent.name)
            existing = store.get(eid)
            if existing is None:
                store[eid] = StoredEntity(
                    id=eid,
                    name=normalize_name(ent.name),
                    type=ent.type,
                    metadata=dict(ent.metadata),
                )
            else:
                existing.metadata.update(ent.metadata)
        return len(entities)

    def add_relationships(
        self,
        relationships: list[Relationship],
        *,
        organization_id: str,
        workspace_id: str,
    ) -> int:
        rels = self._rels(organization_id, workspace_id)
        for rel in relationships:
            # Ensure both endpoints exist as entities.
            self.add_entities(
                [
                    Entity(name=rel.source, type=rel.source_type),
                    Entity(name=rel.target, type=rel.target_type),
                ],
                organization_id=organization_id,
                workspace_id=workspace_id,
            )
            src = entity_id(workspace_id, rel.source_type, rel.source)
            tgt = entity_id(workspace_id, rel.target_type, rel.target)
            edge = (src, rel.type, tgt)
            if edge not in rels:
                rels.append(edge)
        return len(relationships)

    def get_entity(
        self,
        name: str,
        *,
        organization_id: str,
        workspace_id: str,
        type: str | None = None,
    ) -> StoredEntity | None:
        target = normalize_name(name).lower()
        for ent in self._ents(organization_id, workspace_id).values():
            if ent.name.lower() == target and (type is None or ent.type == type):
                return ent
        return None

    def search_entities(
        self,
        text: str,
        *,
        organization_id: str,
        workspace_id: str,
        limit: int = 10,
    ) -> list[StoredEntity]:
        needle = normalize_name(text).lower()
        if not needle:
            return []
        matches = [
            ent
            for ent in self._ents(organization_id, workspace_id).values()
            if needle in ent.name.lower() or ent.name.lower() in needle
        ]
        matches.sort(key=lambda e: len(e.name))  # prefer tighter matches
        return matches[:limit]

    def neighbors(
        self,
        entity_id: str,
        *,
        organization_id: str,
        workspace_id: str,
        depth: int = 1,
    ) -> list[GraphFact]:
        store = self._ents(organization_id, workspace_id)
        edges = self._rels(organization_id, workspace_id)
        if entity_id not in store:
            return []

        facts: list[GraphFact] = []
        seen_edges: set[tuple[str, str, str]] = set()
        visited: set[str] = {entity_id}
        frontier: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while frontier:
            node, dist = frontier.popleft()
            if dist >= depth:
                continue
            for src, rel, tgt in edges:
                if src != node and tgt != node:
                    continue
                if (src, rel, tgt) not in seen_edges:
                    seen_edges.add((src, rel, tgt))
                    facts.append(
                        GraphFact(
                            source=store[src].name if src in store else src,
                            relation=rel,
                            target=store[tgt].name if tgt in store else tgt,
                        )
                    )
                neighbor = tgt if src == node else src
                if neighbor not in visited:
                    visited.add(neighbor)
                    frontier.append((neighbor, dist + 1))
        return facts

    def clear(self, *, organization_id: str, workspace_id: str) -> None:
        self._entities.pop((organization_id, workspace_id), None)
        self._edges.pop((organization_id, workspace_id), None)
