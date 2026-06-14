import io

from app.notifications.base import Notification
from app.notifications.channels import InMemoryChannel
from app.notifications.notifier import Notifier
from tests.conftest import register_and_login


def test_in_memory_channel_collects():
    ch = InMemoryChannel()
    assert ch.send(Notification(title="hi"))
    assert len(ch.sent) == 1 and ch.sent[0].title == "hi"


def test_notifier_respects_min_level():
    ch = InMemoryChannel()
    notifier = Notifier([ch], min_level="warning")
    assert notifier.notify(Notification(title="low", level="info")) is False
    assert notifier.notify(Notification(title="boom", level="error")) is True
    assert len(ch.sent) == 1  # only the error passed the threshold


async def _workspace(client, headers, name="KB"):
    res = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    return res.json()["id"]


async def _upload(client, headers, ws, filename="note.txt"):
    files = {"file": (filename, io.BytesIO(b"hello world content"), "text/plain")}
    return await client.post(
        f"/api/v1/workspaces/{ws}/documents", files=files, headers=headers
    )


async def test_upload_creates_notification_and_marks_read(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _workspace(client, ctx["headers"])
    await _upload(client, ctx["headers"], ws)

    res = await client.get("/api/v1/notifications", headers=ctx["headers"])
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) >= 1
    assert items[0]["event_type"] == "ingestion"
    assert items[0]["level"] == "success"
    assert items[0]["read"] is False

    before = (
        await client.get("/api/v1/notifications/unread_count", headers=ctx["headers"])
    ).json()["unread"]
    assert before >= 1

    nid = items[0]["id"]
    r = await client.post(f"/api/v1/notifications/{nid}/read", headers=ctx["headers"])
    assert r.status_code == 200 and r.json()["read"] is True

    after = (
        await client.get("/api/v1/notifications/unread_count", headers=ctx["headers"])
    ).json()["unread"]
    assert after == before - 1


async def test_mark_all_read_clears_unread(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _workspace(client, ctx["headers"])
    await _upload(client, ctx["headers"], ws, "a.txt")
    await _upload(client, ctx["headers"], ws, "b.txt")

    await client.post("/api/v1/notifications/read_all", headers=ctx["headers"])
    unread = (
        await client.get("/api/v1/notifications/unread_count", headers=ctx["headers"])
    ).json()["unread"]
    assert unread == 0


async def test_notifications_isolated_by_tenant(client):
    a = await register_and_login(client, "a@acme.com", org="Acme")
    b = await register_and_login(client, "b@globex.com", org="Globex")
    ws = await _workspace(client, a["headers"])
    await _upload(client, a["headers"], ws)

    # Globex sees none of Acme's notifications.
    res = await client.get("/api/v1/notifications", headers=b["headers"])
    assert res.json() == []
