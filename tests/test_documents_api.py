import io

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio

DOC_A = b"Revenue grew 20 percent in the third quarter driven by cloud services."
DOC_B = b"The legal team reviewed the data processing agreement with the vendor."


async def _make_workspace(client, headers, name="Knowledge"):
    res = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    return res.json()["id"]


async def _upload(client, headers, ws_id, content: bytes, name="doc.txt"):
    files = {"file": (name, io.BytesIO(content), "text/plain")}
    return await client.post(
        f"/api/v1/workspaces/{ws_id}/documents", files=files, headers=headers
    )


async def test_upload_and_list_document(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])

    up = await _upload(client, ctx["headers"], ws, DOC_A, "q3.txt")
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["status"] == "ready"
    assert body["num_chunks"] >= 1

    listed = await client.get(f"/api/v1/workspaces/{ws}/documents", headers=ctx["headers"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_unsupported_file_rejected(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])
    files = {"file": ("data.xyz", io.BytesIO(b"nope"), "application/octet-stream")}
    res = await client.post(
        f"/api/v1/workspaces/{ws}/documents", files=files, headers=ctx["headers"]
    )
    assert res.status_code == 415


async def test_search_returns_relevant_chunk(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])
    await _upload(client, ctx["headers"], ws, DOC_A, "q3.txt")
    await _upload(client, ctx["headers"], ws, DOC_B, "legal.txt")

    res = await client.post(
        f"/api/v1/workspaces/{ws}/search",
        json={"query": "revenue cloud services", "limit": 1},
        headers=ctx["headers"],
    )
    assert res.status_code == 200
    hits = res.json()
    assert hits
    assert "Revenue" in hits[0]["text"]
    assert hits[0]["source"] == "q3.txt"


async def test_search_is_tenant_isolated(client):
    """Org B must not retrieve Org A's documents even with a matching query."""
    a = await register_and_login(client, "a@orga.com", org="Org A")
    b = await register_and_login(client, "b@orgb.com", org="Org B")

    ws_a = await _make_workspace(client, a["headers"], "A-space")
    await _upload(client, a["headers"], ws_a, DOC_A, "secret.txt")

    ws_b = await _make_workspace(client, b["headers"], "B-space")
    res = await client.post(
        f"/api/v1/workspaces/{ws_b}/search",
        json={"query": "revenue cloud services"},
        headers=b["headers"],
    )
    assert res.status_code == 200
    assert res.json() == []


async def test_delete_document(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _make_workspace(client, ctx["headers"])
    up = await _upload(client, ctx["headers"], ws, DOC_A, "q3.txt")
    doc_id = up.json()["id"]

    res = await client.delete(f"/api/v1/documents/{doc_id}", headers=ctx["headers"])
    assert res.status_code == 204

    listed = await client.get(f"/api/v1/workspaces/{ws}/documents", headers=ctx["headers"])
    assert listed.json() == []
