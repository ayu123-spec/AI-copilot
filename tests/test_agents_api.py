"""API tests for the agentic endpoints (Phase 3, Part 6)."""

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def _new_workspace(client, headers, name="KB"):
    res = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def test_run_agent_persists_and_routes_to_research(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])

    res = await client.post(
        f"/api/v1/workspaces/{ws}/agents/run",
        json={"query": "Explain our onboarding policy"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["run_id"]
    assert body["agent"] == "research"
    assert body["answer"]
    assert body["conversation_id"]  # history was persisted

    got = await client.get(
        f"/api/v1/agents/runs/{body['run_id']}", headers=ctx["headers"]
    )
    assert got.status_code == 200
    assert got.json()["agent"] == "research"


async def test_run_agent_routes_quantitative_to_sql(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])

    res = await client.post(
        f"/api/v1/workspaces/{ws}/agents/run",
        json={"query": "What was total revenue by region last quarter?"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["agent"] == "sql"
    # The fake generator can't emit valid SQL, so the agent fails gracefully —
    # but the run is still produced and recorded.
    assert body["answer"]


async def test_force_specific_agent_overrides_routing(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])

    res = await client.post(
        f"/api/v1/workspaces/{ws}/agents/run",
        json={"query": "total revenue by region", "agent": "research"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    assert res.json()["agent"] == "research"  # forced despite quantitative phrasing


async def test_unknown_forced_agent_is_400(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])
    res = await client.post(
        f"/api/v1/workspaces/{ws}/agents/run",
        json={"query": "hello", "agent": "nope"},
        headers=ctx["headers"],
    )
    assert res.status_code == 400


async def test_list_runs_is_workspace_scoped(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws_a = await _new_workspace(client, ctx["headers"], "A")
    ws_b = await _new_workspace(client, ctx["headers"], "B")
    await client.post(
        f"/api/v1/workspaces/{ws_a}/agents/run",
        json={"query": "explain the policy"},
        headers=ctx["headers"],
    )

    runs_a = (
        await client.get(
            f"/api/v1/workspaces/{ws_a}/agents/runs", headers=ctx["headers"]
        )
    ).json()
    runs_b = (
        await client.get(
            f"/api/v1/workspaces/{ws_b}/agents/runs", headers=ctx["headers"]
        )
    ).json()
    assert len(runs_a) == 1
    assert runs_a[0]["steps"]  # the trace was persisted
    assert runs_b == []


async def test_get_run_cross_org_is_404(client):
    ctx1 = await register_and_login(client, "a@one.com", org="One")
    ws1 = await _new_workspace(client, ctx1["headers"])
    run_id = (
        await client.post(
            f"/api/v1/workspaces/{ws1}/agents/run",
            json={"query": "explain the policy"},
            headers=ctx1["headers"],
        )
    ).json()["run_id"]

    ctx2 = await register_and_login(client, "b@two.com", org="Two")
    got = await client.get(f"/api/v1/agents/runs/{run_id}", headers=ctx2["headers"])
    assert got.status_code == 404


async def test_memory_add_list_and_recall(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _new_workspace(client, ctx["headers"])

    add = await client.post(
        f"/api/v1/workspaces/{ws}/memories",
        json={"content": "The launch date is in March.", "kind": "fact"},
        headers=ctx["headers"],
    )
    assert add.status_code == 201, add.text
    assert add.json()["content"] == "The launch date is in March."

    listed = (
        await client.get(f"/api/v1/workspaces/{ws}/memories", headers=ctx["headers"])
    ).json()
    assert len(listed) == 1

    rec = await client.post(
        f"/api/v1/workspaces/{ws}/memories/recall",
        json={"query": "When is the launch?"},
        headers=ctx["headers"],
    )
    assert rec.status_code == 200
    hits = rec.json()
    assert hits and "March" in hits[0]["content"]


async def test_memory_is_workspace_scoped(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws_a = await _new_workspace(client, ctx["headers"], "A")
    ws_b = await _new_workspace(client, ctx["headers"], "B")

    await client.post(
        f"/api/v1/workspaces/{ws_a}/memories",
        json={"content": "workspace A only secret"},
        headers=ctx["headers"],
    )
    rec = await client.post(
        f"/api/v1/workspaces/{ws_b}/memories/recall",
        json={"query": "secret"},
        headers=ctx["headers"],
    )
    assert rec.json() == []
