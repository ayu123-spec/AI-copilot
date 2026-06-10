import io

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_chat_returns_answer_with_citations(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = (await client.post("/api/v1/workspaces", json={"name": "KB"}, headers=ctx["headers"])).json()["id"]
    files = {"file": ("q3.txt", io.BytesIO(b"Revenue grew 20 percent in the third quarter driven by cloud services."), "text/plain")}
    await client.post(f"/api/v1/workspaces/{ws}/documents", files=files, headers=ctx["headers"])

    res = await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "How did revenue do this quarter?"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["answer"]
    assert body["citations"]
    assert body["citations"][0]["source"] == "q3.txt"


async def test_chat_with_no_documents_returns_no_citations(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = (await client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=ctx["headers"])).json()["id"]
    res = await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "anything at all"},
        headers=ctx["headers"],
    )
    assert res.status_code == 200
    assert res.json()["citations"] == []


async def test_chat_unknown_workspace_404(client):
    ctx = await register_and_login(client, "admin@acme.com")
    res = await client.post(
        "/api/v1/workspaces/doesnotexist/chat",
        json={"query": "hi"},
        headers=ctx["headers"],
    )
    assert res.status_code == 404
