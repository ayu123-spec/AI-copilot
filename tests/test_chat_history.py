import io

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def _setup(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = (await client.post("/api/v1/workspaces", json={"name": "KB"}, headers=ctx["headers"])).json()["id"]
    files = {"file": ("q3.txt", io.BytesIO(b"Revenue grew 20 percent in the third quarter."), "text/plain")}
    await client.post(f"/api/v1/workspaces/{ws}/documents", files=files, headers=ctx["headers"])
    return ctx["headers"], ws


async def test_chat_creates_conversation_and_saves_history(client):
    H, ws = await _setup(client)
    res = await client.post(f"/api/v1/workspaces/{ws}/chat", json={"query": "How was revenue?"}, headers=H)
    body = res.json()
    assert body["conversation_id"] and body["message_id"]

    convs = await client.get(f"/api/v1/workspaces/{ws}/conversations", headers=H)
    assert len(convs.json()) == 1

    msgs = await client.get(f"/api/v1/conversations/{body['conversation_id']}/messages", headers=H)
    roles = [m["role"] for m in msgs.json()]
    assert roles == ["user", "assistant"]
    assert msgs.json()[1]["citations"]  # assistant message carries citations


async def test_chat_continues_existing_conversation(client):
    H, ws = await _setup(client)
    first = (await client.post(f"/api/v1/workspaces/{ws}/chat", json={"query": "Q1?"}, headers=H)).json()
    conv_id = first["conversation_id"]
    await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "Q2?", "conversation_id": conv_id},
        headers=H,
    )
    msgs = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=H)
    assert len(msgs.json()) == 4  # two turns -> two user + two assistant


async def test_feedback_records_on_message(client):
    H, ws = await _setup(client)
    chat = (await client.post(f"/api/v1/workspaces/{ws}/chat", json={"query": "hi"}, headers=H)).json()
    res = await client.post(
        f"/api/v1/messages/{chat['message_id']}/feedback",
        json={"rating": "up"},
        headers=H,
    )
    assert res.status_code == 200
    assert res.json()["feedback"] == "up"


async def test_chat_stream_emits_tokens_and_citations(client):
    H, ws = await _setup(client)
    collected = ""
    async with client.stream(
        "POST",
        f"/api/v1/workspaces/{ws}/chat/stream",
        json={"query": "How was revenue?"},
        headers=H,
    ) as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            collected += line
    assert "token" in collected
    assert "done" in collected
