"""Neo4j-backed knowledge-graph store (production backend).

Lazily imports the ``neo4j`` driver so the module always loads even when the
package isn't installed and the default in-memory backend is in use. Entities
are ``:Entity`` nodes keyed by a deterministic id; relationships are ``:REL``
edges carrying their semantic type as a property (avoiding dynamic relationship
labels, which can't be parameterised safely). Multi-hop traversal is a
breadth-first walk in Python over a simple one-hop query, matching the
in-memory store's semantics. Not exercised by the offline test suite.
"""

from collections import deque

from app.core.config import settings
from app.graph.base import (
    Entity,
    GraphFact,
    GraphStore,
    Relationship,
    StoredEntity,
    entity_id,
    normalize_name,
)


class Neo4jGraphStore(GraphStore):  # pragma: no cover - requires a live server
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise ImportError("Neo4j backend needs: pip install neo4j") from exc
        self._driver = GraphDatabase.driver(
            uri or settings.NEO4J_URI,
            auth=(user or settings.NEO4J_USER, password or settings.NEO4J_PASSWORD),
        )

    def close(self) -> None:
        self._driver.close()

    def add_entities(
        self, entities: list[Entity], *, organization_id: str, workspace_id: str
    ) -> int:
        rows = [
            {
                "id": entity_id(workspace_id, e.type, e.name),
                "name": normalize_name(e.name),
                "type": e.type,
                "org": organization_id,
                "ws": workspace_id,
            }
            for e in entities
        ]
        with self._driver.session() as session:
            session.run(
                """
                UNWIND $rows AS row
                MERGE (e:Entity {id: row.id})
                SET e.name = row.name, e.type = row.type,
                    e.organization_id = row.org, e.workspace_id = row.ws
                """,
                rows=rows,
            )
        return len(entities)

    def add_relationships(
        self,
        relationships: list[Relationship],
        *,
        organization_id: str,
        workspace_id: str,
    ) -> int:
        rows = []
        for r in relationships:
            rows.append(
                {
                    "src": entity_id(workspace_id, r.source_type, r.source),
                    "src_name": normalize_name(r.source),
                    "src_type": r.source_type,
                    "tgt": entity_id(workspace_id, r.target_type, r.target),
                    "tgt_name": normalize_name(r.target),
                    "tgt_type": r.target_type,
                    "type": r.type,
                    "org": organization_id,
                    "ws": workspace_id,
                }
            )
        with self._driver.session() as session:
            session.run(
                """
                UNWIND $rows AS row
                MERGE (a:Entity {id: row.src})
                  ON CREATE SET a.name = row.src_name, a.type = row.src_type,
                                a.organization_id = row.org, a.workspace_id = row.ws
                MERGE (b:Entity {id: row.tgt})
                  ON CREATE SET b.name = row.tgt_name, b.type = row.tgt_type,
                                b.organization_id = row.org, b.workspace_id = row.ws
                MERGE (a)-[rel:REL {type: row.type}]->(b)
                """,
                rows=rows,
            )
        return len(relationships)

    def get_entity(
        self,
        name: str,
        *,
        organization_id: str,
        workspace_id: str,
        type: str | None = None,
    ) -> StoredEntity | None:
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (e:Entity)
                WHERE e.organization_id = $org AND e.workspace_id = $ws
                  AND toLower(e.name) = toLower($name)
                  AND ($type IS NULL OR e.type = $type)
                RETURN e.id AS id, e.name AS name, e.type AS type
                LIMIT 1
                """,
                org=organization_id,
                ws=workspace_id,
                name=normalize_name(name),
                type=type,
            ).single()
        if record is None:
            return None
        return StoredEntity(id=record["id"], name=record["name"], type=record["type"])

    def search_entities(
        self,
        text: str,
        *,
        organization_id: str,
        workspace_id: str,
        limit: int = 10,
    ) -> list[StoredEntity]:
        needle = normalize_name(text)
        if not needle:
            return []
        with self._driver.session() as session:
            records = session.run(
                """
                MATCH (e:Entity)
                WHERE e.organization_id = $org AND e.workspace_id = $ws
                  AND toLower(e.name) CONTAINS toLower($needle)
                RETURN e.id AS id, e.name AS name, e.type AS type
                ORDER BY size(e.name) ASC
                LIMIT $limit
                """,
                org=organization_id,
                ws=workspace_id,
                needle=needle,
                limit=limit,
            )
            return [
                StoredEntity(id=r["id"], name=r["name"], type=r["type"])
                for r in records
            ]

    def _one_hop(self, session, node_id, org, ws):
        return session.run(
            """
            MATCH (s:Entity {id: $id})-[rel:REL]-(t:Entity)
            WHERE s.organization_id = $org AND s.workspace_id = $ws
            RETURN startNode(rel).name AS source, rel.type AS relation,
                   endNode(rel).name AS target,
                   startNode(rel).id AS source_id, endNode(rel).id AS target_id
            """,
            id=node_id,
            org=org,
            ws=ws,
        ).data()

    def neighbors(
        self,
        entity_id: str,
        *,
        organization_id: str,
        workspace_id: str,
        depth: int = 1,
    ) -> list[GraphFact]:
        facts: list[GraphFact] = []
        seen: set[tuple[str, str, str]] = set()
        visited = {entity_id}
        frontier: deque[tuple[str, int]] = deque([(entity_id, 0)])
        with self._driver.session() as session:
            while frontier:
                node, dist = frontier.popleft()
                if dist >= depth:
                    continue
                for row in self._one_hop(session, node, organization_id, workspace_id):
                    key = (row["source_id"], row["relation"], row["target_id"])
                    if key not in seen:
                        seen.add(key)
                        facts.append(
                            GraphFact(
                                source=row["source"],
                                relation=row["relation"],
                                target=row["target"],
                            )
                        )
                    nxt = (
                        row["target_id"]
                        if row["source_id"] == node
                        else row["source_id"]
                    )
                    if nxt not in visited:
                        visited.add(nxt)
                        frontier.append((nxt, dist + 1))
        return facts

    def clear(self, *, organization_id: str, workspace_id: str) -> None:
        with self._driver.session() as session:
            session.run(
                """
                MATCH (e:Entity)
                WHERE e.organization_id = $org AND e.workspace_id = $ws
                DETACH DELETE e
                """,
                org=organization_id,
                ws=workspace_id,
            )
