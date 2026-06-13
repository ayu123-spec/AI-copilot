"""Tests for the GraphAgent (Phase 4, Module 13)."""

from app.agents.base import AgentContext
from app.agents.graph_agent import GraphAgent
from app.chunking.chunkers import Chunk
from app.embeddings.embedders import FakeEmbedder
from app.graph import (
    GraphRetriever,
    InMemoryGraphStore,
    RuleBasedEntityExtractor,
    build_graph_from_texts,
)
from app.rag.engine import RagEngine
from app.rag.hybrid import HybridRetriever
from app.rag.llm import FakeGenerator
from app.rag.rerank import FakeReranker
from app.vectorstore.qdrant_store import VectorStore


def _engine(embedder, *, with_docs):
    store = VectorStore(collection="graph_agent_docs", location=":memory:")
    store.ensure_collection(embedder.dimension)
    if with_docs:
        chunks = [
            Chunk(
                text="Alice Johnson reports to Bob Smith in Engineering.",
                metadata={"source": "org.txt", "workspace_id": "w"},
            )
        ]
        store.upsert_chunks(chunks, embedder.embed([c.text for c in chunks]))
    return RagEngine(HybridRetriever(store, embedder), FakeReranker(), FakeGenerator())


def _graph():
    store = InMemoryGraphStore()
    build_graph_from_texts(
        store,
        RuleBasedEntityExtractor(),
        [
            "Alice Johnson reports to Bob Smith.",
            "Bob Smith manages the Engineering department.",
        ],
        organization_id="o",
        workspace_id="w",
    )
    return store


def test_graph_agent_fuses_facts_and_evidence():
    emb = FakeEmbedder(dim=64)
    agent = GraphAgent(
        GraphRetriever(_graph(), max_hops=1), _engine(emb, with_docs=True)
    )
    run = agent.run(
        "Who does Alice Johnson report to?",
        AgentContext(organization_id="o", workspace_id="w"),
    )
    assert run.answer
    assert "Alice Johnson —REPORTS_TO→ Bob Smith" in run.metadata["graph_facts"]
    assert run.metadata["entities"]
    tools = [s.tool for s in run.steps if s.tool]
    assert "graph_traverse" in tools and "rag_search" in tools


def test_graph_agent_no_info_path():
    emb = FakeEmbedder(dim=64)
    agent = GraphAgent(
        GraphRetriever(InMemoryGraphStore()), _engine(emb, with_docs=False)
    )
    run = agent.run(
        "Who is Zaphod Beeblebrox?",
        AgentContext(organization_id="o", workspace_id="w"),
    )
    assert "enough information" in run.answer.lower()
