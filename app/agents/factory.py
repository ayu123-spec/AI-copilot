"""Assemble the default agent registry and orchestrator from runtime parts.

Keeps endpoint code thin: given the embedder, vector store, re-ranker,
generator and analytics engine, this wires up the research and SQL agents and
the orchestrator that routes between them.
"""

from sqlalchemy.engine import Engine

from app.agents.orchestrator import Orchestrator, Router, keyword_router
from app.agents.registry import AgentRegistry
from app.agents.research import ResearchAgent
from app.agents.sql import ALLOWED_TABLES, SqlAgent, SqlQueryTool, schema_description
from app.embeddings.base import Embedder
from app.rag.engine import RagEngine
from app.rag.hybrid import HybridRetriever
from app.rag.llm import Generator
from app.rag.rerank import Reranker
from app.vectorstore.qdrant_store import VectorStore


def build_registry(
    *,
    embedder: Embedder,
    store: VectorStore,
    reranker: Reranker,
    generator: Generator,
    analytics_engine: Engine,
    graph_store=None,
    max_rows: int = 100,
    max_hops: int = 2,
) -> AgentRegistry:
    """A registry with the research and SQL agents wired to real backends, plus
    the graph agent when a ``graph_store`` is supplied."""
    engine = RagEngine(HybridRetriever(store, embedder), reranker, generator)
    sql_tool = SqlQueryTool(analytics_engine, ALLOWED_TABLES, max_rows=max_rows)

    registry = AgentRegistry()
    registry.register(ResearchAgent(engine))
    registry.register(SqlAgent(generator, sql_tool, schema_description()))
    if graph_store is not None:
        from app.agents.graph_agent import GraphAgent
        from app.graph import GraphRetriever

        retriever = GraphRetriever(graph_store, max_hops=max_hops)
        registry.register(GraphAgent(retriever, engine))
    return registry


def build_orchestrator(
    *,
    embedder: Embedder,
    store: VectorStore,
    reranker: Reranker,
    generator: Generator,
    analytics_engine: Engine,
    graph_store=None,
    max_rows: int = 100,
    max_hops: int = 2,
    router: Router | None = None,
) -> Orchestrator:
    """The default orchestrator. Uses the deterministic keyword router unless a
    router is supplied (e.g. ``make_llm_router(...)`` for LLM-driven routing)."""
    registry = build_registry(
        embedder=embedder,
        store=store,
        reranker=reranker,
        generator=generator,
        analytics_engine=analytics_engine,
        graph_store=graph_store,
        max_rows=max_rows,
        max_hops=max_hops,
    )
    return Orchestrator(
        registry, router=router or keyword_router, default_agent="research"
    )
