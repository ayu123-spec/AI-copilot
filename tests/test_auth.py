import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_register_login_me(client):
    ctx = await register_and_login(client, "admin@acme.com")
    assert ctx["user"]["role"] == "admin"
    assert ctx["user"]["is_verified"] is False

    me = await client.get("/api/v1/users/me", headers=ctx["headers"])
    assert me.status_code == 200
    assert me.json()["email"] == "admin@acme.com"


async def test_duplicate_email_rejected(client):
    await register_and_login(client, "dup@acme.com")
    second = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@acme.com",
            "password": "supersecret123",
            "full_name": "Other",
            "organization_name": "Other Inc",
        },
    )
    assert second.status_code == 409


async def test_wrong_password_rejected(client):
    await register_and_login(client, "x@acme.com")
    bad = await client.post(
        "/api/v1/auth/login", json={"email": "x@acme.com", "password": "wrong"}
    )
    assert bad.status_code == 401


async def test_refresh_token_issues_access(client):
    await register_and_login(client, "r@acme.com")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "r@acme.com", "password": "supersecret123"},
    )
    refresh = login.json()["refresh_token"]
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200
    assert "access_token" in res.json()


async def test_refresh_rejects_access_token(client):
    ctx = await register_and_login(client, "r2@acme.com")
    access = ctx["headers"]["Authorization"].split()[1]
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert res.status_code == 401


async def test_unauthenticated_blocked(client):
    res = await client.get("/api/v1/users/me")
    assert res.status_code in (401, 403)
