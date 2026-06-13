"""GraphRAG retrieval.

Turns a natural-language query into knowledge-graph facts: spot the entities the
query mentions, locate them in the graph, and traverse their relationships up to
``max_hops`` hops. The resulting :class:`GraphContext` renders as bullet facts
that a generator can fuse with vector-retrieved passages — letting the system
answer multi-hop, relationship questions that pure vector search cannot.
"""

from dataclasses import dataclass, field

from app.graph.base import GraphFact, GraphStore, StoredEntity
from app.graph.extract import extract_candidate_names


@dataclass
class GraphContext:
    entities: list[StoredEntity] = field(default_factory=list)
    facts: list[GraphFact] = field(default_factory=list)

    def as_text(self) -> str:
        """Render facts as a bullet list for prompting; empty if there are none."""
        return "\n".join(f"- {f.as_text()}" for f in self.facts)


class GraphRetriever:
    def __init__(
        self,
        store: GraphStore,
        *,
        max_hops: int = 2,
        max_entities: int = 5,
    ) -> None:
        self._store = store
        self._max_hops = max_hops
        self._max_entities = max_entities

    def _seed_entities(
        self, query: str, *, organization_id: str, workspace_id: str
    ) -> list[StoredEntity]:
        seeds: list[StoredEntity] = []
        seen: set[str] = set()
        for name in extract_candidate_names(query):
            exact = self._store.get_entity(
                name, organization_id=organization_id, workspace_id=workspace_id
            )
            candidates = (
                [exact]
                if exact
                else self._store.search_entities(
                    name,
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    limit=3,
                )
            )
            for ent in candidates:
                if ent and ent.id not in seen:
                    seen.add(ent.id)
                    seeds.append(ent)
        return seeds[: self._max_entities]

    def retrieve(
        self,
        query: str,
        *,
        organization_id: str,
        workspace_id: str,
        depth: int | None = None,
    ) -> GraphContext:
        hops = self._max_hops if depth is None else depth
        seeds = self._seed_entities(
            query, organization_id=organization_id, workspace_id=workspace_id
        )

        facts: list[GraphFact] = []
        seen: set[tuple[str, str, str]] = set()
        for seed in seeds:
            for fact in self._store.neighbors(
                seed.id,
                organization_id=organization_id,
                workspace_id=workspace_id,
                depth=hops,
            ):
                key = (fact.source, fact.relation, fact.target)
                if key not in seen:
                    seen.add(key)
                    facts.append(fact)
        return GraphContext(entities=seeds, facts=facts)
