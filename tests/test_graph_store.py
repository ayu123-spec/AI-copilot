"""Tests for the in-memory graph store (Phase 4, Module 12)."""

import pytest

from app.graph import Entity, InMemoryGraphStore, Relationship, entity_id


@pytest.fixture
def store():
    return InMemoryGraphStore()


def test_add_and_get_entity(store):
    store.add_entities(
        [Entity("Acme Corp", "Company")], organization_id="o", workspace_id="w"
    )
    ent = store.get_entity("acme corp", organization_id="o", workspace_id="w")
    assert ent and ent.type == "Company"


def test_relationship_creates_endpoints_and_neighbors(store):
    store.add_relationships(
        [Relationship("Alice", "Acme", "WORKS_FOR", "Person", "Company")],
        organization_id="o",
        workspace_id="w",
    )
    alice = entity_id("w", "Person", "Alice")
    facts = store.neighbors(alice, organization_id="o", workspace_id="w", depth=1)
    assert "Alice —WORKS_FOR→ Acme" in {f.as_text() for f in facts}


def test_multi_hop_traversal(store):
    store.add_relationships(
        [
            Relationship("Bob", "Carol", "REPORTS_TO", "Person", "Person"),
            Relationship("Carol", "Dave", "REPORTS_TO", "Person", "Person"),
        ],
        organization_id="o",
        workspace_id="w",
    )
    bob = entity_id("w", "Person", "Bob")
    one = store.neighbors(bob, organization_id="o", workspace_id="w", depth=1)
    two = store.neighbors(bob, organization_id="o", workspace_id="w", depth=2)
    assert len(one) == 1  # Bob -> Carol
    assert len(two) == 2  # also Carol -> Dave


def test_tenant_isolation(store):
    store.add_relationships(
        [Relationship("Alice", "Acme", "WORKS_FOR", "Person", "Company")],
        organization_id="o",
        workspace_id="w1",
    )
    assert store.search_entities("Alice", organization_id="o", workspace_id="w2") == []
    alice = entity_id("w1", "Person", "Alice")
    assert store.neighbors(alice, organization_id="o", workspace_id="w2", depth=1) == []


def test_clear(store):
    store.add_entities(
        [Entity("Acme", "Company")], organization_id="o", workspace_id="w"
    )
    store.clear(organization_id="o", workspace_id="w")
    assert store.get_entity("Acme", organization_id="o", workspace_id="w") is None


def test_export_graph(store):
    store.add_relationships(
        [Relationship("Alice", "Acme", "WORKS_FOR", "Person", "Company")],
        organization_id="o",
        workspace_id="w",
    )
    entities, facts = store.export_graph(organization_id="o", workspace_id="w")
    assert {"Alice", "Acme"} <= {e.name for e in entities}
    assert "Alice —WORKS_FOR→ Acme" in {f.as_text() for f in facts}
