"""Build a workspace's knowledge graph from text.

Runs the configured extractor over each text block and upserts the resulting
entities and relationships into the graph store, scoped to the tenant. The
source text typically comes from the workspace's already-ingested document
chunks, so the graph stays consistent with what RAG retrieves over.
"""

from dataclasses import dataclass

from app.graph.base import GraphStore
from app.graph.extract import EntityExtractor


@dataclass
class GraphBuildResult:
    entities: int
    relationships: int


def build_graph_from_texts(
    store: GraphStore,
    extractor: EntityExtractor,
    texts: list[str],
    *,
    organization_id: str,
    workspace_id: str,
) -> GraphBuildResult:
    total_entities = 0
    total_relationships = 0
    for text in texts:
        result = extractor.extract(text)
        if result.entities:
            store.add_entities(
                result.entities,
                organization_id=organization_id,
                workspace_id=workspace_id,
            )
            total_entities += len(result.entities)
        if result.relationships:
            store.add_relationships(
                result.relationships,
                organization_id=organization_id,
                workspace_id=workspace_id,
            )
            total_relationships += len(result.relationships)
    return GraphBuildResult(entities=total_entities, relationships=total_relationships)
