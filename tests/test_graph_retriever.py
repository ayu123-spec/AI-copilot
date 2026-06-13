"""Tests for GraphRAG retrieval (Phase 4, Module 13)."""

from app.graph import (
    GraphRetriever,
    InMemoryGraphStore,
    RuleBasedEntityExtractor,
    build_graph_from_texts,
)


def _populate(store):
    build_graph_from_texts(
        store,
        RuleBasedEntityExtractor(),
        [
            "Alice Johnson works for Acme Corp.",
            "Alice Johnson reports to Bob Smith.",
            "Bob Smith manages the Engineering department.",
        ],
        organization_id="o",
        workspace_id="w",
    )


def test_graphrag_retrieves_facts_for_query():
    store = InMemoryGraphStore()
    _populate(store)
    ctx = GraphRetriever(store, max_hops=1).retrieve(
        "Who does Alice Johnson report to?", organization_id="o", workspace_id="w"
    )
    assert "Alice Johnson —REPORTS_TO→ Bob Smith" in {f.as_text() for f in ctx.facts}
    assert ctx.entities  # Alice Johnson found as a seed


def test_graphrag_multi_hop_reaches_second_degree():
    store = InMemoryGraphStore()
    _populate(store)
    ctx = GraphRetriever(store, max_hops=2).retrieve(
        "Tell me about Alice Johnson", organization_id="o", workspace_id="w"
    )
    facts = {f.as_text() for f in ctx.facts}
    assert any("Bob Smith" in f and "MANAGES" in f for f in facts)


def test_graphrag_empty_for_unknown_entity():
    store = InMemoryGraphStore()
    _populate(store)
    ctx = GraphRetriever(store).retrieve(
        "Who is Zaphod Beeblebrox?", organization_id="o", workspace_id="w"
    )
    assert ctx.facts == []
