"""Knowledge graph + GraphRAG (Phase 4).

A tenant-scoped property graph of entities and relationships extracted from
documents, with multi-hop traversal that fuses into the RAG pipeline.
"""

from app.graph.base import (
    Entity,
    GraphFact,
    GraphStore,
    Relationship,
    StoredEntity,
    entity_id,
    normalize_name,
)
from app.graph.builder import GraphBuildResult, build_graph_from_texts
from app.graph.extract import (
    EntityExtractor,
    ExtractionResult,
    LLMEntityExtractor,
    RuleBasedEntityExtractor,
    extract_candidate_names,
)
from app.graph.factory import get_entity_extractor, get_graph_store
from app.graph.memory_store import InMemoryGraphStore
from app.graph.retriever import GraphContext, GraphRetriever

__all__ = [
    "Entity",
    "Relationship",
    "StoredEntity",
    "GraphFact",
    "GraphStore",
    "InMemoryGraphStore",
    "entity_id",
    "normalize_name",
    "EntityExtractor",
    "RuleBasedEntityExtractor",
    "LLMEntityExtractor",
    "ExtractionResult",
    "extract_candidate_names",
    "build_graph_from_texts",
    "GraphBuildResult",
    "GraphRetriever",
    "GraphContext",
    "get_graph_store",
    "get_entity_extractor",
]
