"""API tests for the knowledge graph + GraphRAG (Phase 4)."""

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio

_CORPUS = [
    "Alice Johnson works for Acme Corp.",
    "Alice Johnson reports to Bob Smith.",
    "Bob Smith manages the Engineering department.",
]


async def _new_workspace(client, headers, name="KB"):
    res = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _build(client, headers, ws, texts=_CORPUS):
    res = await client.post(
        f"/api/v1/workspaces/{ws}/graph/build",
        json={"texts": texts},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_build_graph_from_texts(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    body = await _build(client, ctx["headers"], ws)
    assert body["entities"] > 0
    assert body["relationships"] >= 3


async def test_search_entities_and_neighbors(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    await _build(client, ctx["headers"], ws)

    ents = (
        await client.get(
            f"/api/v1/workspaces/{ws}/graph/entities",
            params={"q": "Alice"},
            headers=ctx["headers"],
        )
    ).json()
    assert any(e["name"] == "Alice Johnson" for e in ents)

    nb = await client.get(
        f"/api/v1/workspaces/{ws}/graph/entities/Alice Johnson/neighbors",
        params={"depth": 1},
        headers=ctx["headers"],
    )
    assert nb.status_code == 200, nb.text
    facts = {(f["source"], f["relation"], f["target"]) for f in nb.json()["facts"]}
    assert ("Alice Johnson", "REPORTS_TO", "Bob Smith") in facts


async def test_neighbors_unknown_entity_404(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    await _build(client, ctx["headers"], ws)
    res = await client.get(
        f"/api/v1/workspaces/{ws}/graph/entities/Nobody/neighbors",
        headers=ctx["headers"],
    )
    assert res.status_code == 404


async def test_graphrag_query_endpoint(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    await _build(client, ctx["headers"], ws)

    res = await client.post(
        f"/api/v1/workspaces/{ws}/graph/query",
        json={"query": "Who does Alice Johnson report to?", "depth": 1},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    facts = {(f["source"], f["relation"], f["target"]) for f in res.json()["facts"]}
    assert ("Alice Johnson", "REPORTS_TO", "Bob Smith") in facts


async def test_graph_is_workspace_scoped(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws_a = await _new_workspace(client, ctx["headers"], "A")
    ws_b = await _new_workspace(client, ctx["headers"], "B")
    await _build(client, ctx["headers"], ws_a)

    ents_b = (
        await client.get(
            f"/api/v1/workspaces/{ws_b}/graph/entities",
            params={"q": "Alice"},
            headers=ctx["headers"],
        )
    ).json()
    assert ents_b == []


async def test_relationship_query_routes_to_graph_agent(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    await _build(client, ctx["headers"], ws)

    res = await client.post(
        f"/api/v1/workspaces/{ws}/agents/run",
        json={"query": "Who does Alice Johnson report to?"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["agent"] == "graph"
    assert body["answer"]
    assert body["metadata"]["graph_facts"]


async def test_get_full_graph(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    await _build(client, ctx["headers"], ws)
    res = await client.get(f"/api/v1/workspaces/{ws}/graph", headers=ctx["headers"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["entities"]) > 0
    assert len(body["facts"]) >= 3
