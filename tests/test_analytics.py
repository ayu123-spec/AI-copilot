import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def _make_workspace(client, headers, name="Metrics"):
    res = await client.post(
        "/api/v1/workspaces", json={"name": name}, headers=headers
    )
    return res.json()["id"]


async def test_analytics_empty_workspace_is_zeroed(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])

    res = await client.get(
        f"/api/v1/workspaces/{ws}/analytics", headers=ctx["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_queries"] == 0
    assert body["conversations"] == 0
    assert body["documents"] == 0
    assert body["query_type_mix"] == []
    assert body["activity"] == []


async def test_analytics_counts_chat_activity_and_query_types(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])

    # Two chats with different intents.
    await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "Analyze my resume"},
        headers=ctx["headers"],
    )
    await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "Summarize the key takeaways"},
        headers=ctx["headers"],
    )

    res = await client.get(
        f"/api/v1/workspaces/{ws}/analytics", headers=ctx["headers"]
    )
    body = res.json()
    assert body["total_queries"] == 2
    assert body["conversations"] == 2
    assert body["messages_user"] == 2
    labels = {item["label"] for item in body["query_type_mix"]}
    assert "resume_analysis" in labels
    assert "summary" in labels
    assert len(body["activity"]) >= 1


async def test_analytics_isolated_by_tenant(client):
    a = await register_and_login(client, "a@acme.com", org="Acme")
    b = await register_and_login(client, "b@globex.com", org="Globex")
    ws_a = await _make_workspace(client, a["headers"])
    await client.post(
        f"/api/v1/workspaces/{ws_a}/chat",
        json={"query": "Analyze my resume"},
        headers=a["headers"],
    )

    # Globex cannot read Acme's workspace analytics.
    res = await client.get(
        f"/api/v1/workspaces/{ws_a}/analytics", headers=b["headers"]
    )
    assert res.status_code == 404
