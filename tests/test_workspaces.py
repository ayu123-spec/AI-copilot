import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_workspace_create_and_list(client):
    ctx = await register_and_login(client, "admin@acme.com")
    created = await client.post(
        "/api/v1/workspaces", json={"name": "Finance"}, headers=ctx["headers"]
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Finance"
    assert "upload_limit_mb" in created.json()["settings"]

    listed = await client.get("/api/v1/workspaces", headers=ctx["headers"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_update_workspace_settings(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await client.post(
        "/api/v1/workspaces", json={"name": "Legal"}, headers=ctx["headers"]
    )
    wid = ws.json()["id"]
    res = await client.patch(
        f"/api/v1/workspaces/{wid}/settings",
        json={"upload_limit_mb": 200},
        headers=ctx["headers"],
    )
    assert res.status_code == 200
    assert res.json()["settings"]["upload_limit_mb"] == 200


async def test_tenant_isolation_workspaces(client):
    """A workspace in org A must never be visible to org B."""
    a = await register_and_login(client, "a@orga.com", org="Org A")
    b = await register_and_login(client, "b@orgb.com", org="Org B")

    await client.post(
        "/api/v1/workspaces", json={"name": "Secret A"}, headers=a["headers"]
    )

    b_list = await client.get("/api/v1/workspaces", headers=b["headers"])
    assert b_list.status_code == 200
    assert b_list.json() == []


async def test_tenant_isolation_users(client):
    """Listing users must only return the caller's organization."""
    a = await register_and_login(client, "a@orga.com", org="Org A")
    await register_and_login(client, "b@orgb.com", org="Org B")

    a_users = await client.get("/api/v1/users", headers=a["headers"])
    assert a_users.status_code == 200
    emails = {u["email"] for u in a_users.json()}
    assert emails == {"a@orga.com"}


async def test_invite_cross_tenant_blocked(client):
    """Cannot invite a user who belongs to a different organization."""
    a = await register_and_login(client, "a@orga.com", org="Org A")
    await register_and_login(client, "b@orgb.com", org="Org B")

    ws = await client.post(
        "/api/v1/workspaces", json={"name": "Team" }, headers=a["headers"]
    )
    wid = ws.json()["id"]
    res = await client.post(
        f"/api/v1/workspaces/{wid}/invite",
        json={"email": "b@orgb.com", "role": "member"},
        headers=a["headers"],
    )
    assert res.status_code == 404
