"""Select the graph store and entity extractor from settings.

The graph store is a process-wide singleton (the in-memory graph must persist
across requests). Neo4j is imported only when selected, so the default path has
no hard dependency on the driver.
"""

from app.core.config import settings
from app.graph.base import GraphStore
from app.graph.extract import EntityExtractor, RuleBasedEntityExtractor

_graph_store: GraphStore | None = None
_rule_extractor: RuleBasedEntityExtractor | None = None


def get_graph_store() -> GraphStore:
    global _graph_store
    if _graph_store is not None:
        return _graph_store
    backend = settings.GRAPH_BACKEND.lower()
    if backend == "memory":
        from app.graph.memory_store import InMemoryGraphStore

        _graph_store = InMemoryGraphStore()
    elif backend == "neo4j":
        from app.graph.neo4j_store import Neo4jGraphStore

        _graph_store = Neo4jGraphStore()
    else:
        raise ValueError(f"Unknown GRAPH_BACKEND: {backend}")
    return _graph_store


def get_entity_extractor(generator=None) -> EntityExtractor:
    backend = settings.GRAPH_ENTITY_EXTRACTOR.lower()
    if backend == "rule":
        global _rule_extractor
        if _rule_extractor is None:
            _rule_extractor = RuleBasedEntityExtractor()
        return _rule_extractor
    if backend == "llm":
        from app.graph.extract import LLMEntityExtractor

        if generator is None:
            from app.rag.llm import get_generator

            generator = get_generator()
        return LLMEntityExtractor(generator)
    raise ValueError(f"Unknown GRAPH_ENTITY_EXTRACTOR: {backend}")
