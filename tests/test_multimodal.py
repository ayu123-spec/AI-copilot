"""Tests for multimodal RAG: image describers + image ingestion/retrieval."""

import struct
import zlib

from app.multimodal.base import ImageDescriber, ImageDescription
from app.multimodal.describers import FakeImageDescriber
from app.multimodal.factory import get_image_describer
from tests.conftest import register_and_login


def _tiny_png() -> bytes:
    """A minimal valid 1x1 PNG (content is irrelevant to the fake describer)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\xff\xff"
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def test_fake_describer_is_deterministic_and_uses_filename():
    d = FakeImageDescriber()
    img = b"some-bytes"
    a = d.describe(img, filename="quarterly_sales_chart.png", content_type="image/png")
    b = d.describe(img, filename="quarterly_sales_chart.png", content_type="image/png")

    assert isinstance(a, ImageDescription)
    assert a.text == b.text  # deterministic
    assert a.metadata["modality"] == "image"
    assert "quarterly sales chart" in a.text.lower()  # filename surfaced
    # different bytes -> different fingerprint
    assert d.describe(b"other").metadata["fingerprint"] != a.metadata["fingerprint"]


def test_factory_defaults_to_fake():
    describer = get_image_describer()
    assert isinstance(describer, ImageDescriber)
    assert isinstance(describer, FakeImageDescriber)


async def test_upload_image_is_described_and_retrievable(client):
    ctx = await register_and_login(client, "vision@acme.com")
    headers = ctx["headers"]
    ws = (
        await client.post("/api/v1/workspaces", headers=headers, json={"name": "Viz"})
    ).json()["id"]

    files = {"file": ("revenue_chart.png", _tiny_png(), "image/png")}
    res = await client.post(
        f"/api/v1/workspaces/{ws}/documents", headers=headers, files=files
    )
    assert res.status_code == 201, res.text
    doc = res.json()
    assert doc["content_type"].startswith("image/")
    assert doc["status"] == "ready"
    assert doc["num_chunks"] >= 1

    # The image's description is now searchable, tagged as image modality.
    search = await client.post(
        f"/api/v1/workspaces/{ws}/search",
        headers=headers,
        json={"query": "revenue chart", "limit": 5},
    )
    assert search.status_code == 200, search.text
    results = search.json()
    assert len(results) >= 1
    assert any(r["modality"] == "image" for r in results)


async def test_image_isolated_to_workspace(client):
    """An image uploaded to one workspace is not searchable from another."""
    ctx = await register_and_login(client, "iso@acme.com")
    headers = ctx["headers"]
    ws_a = (
        await client.post("/api/v1/workspaces", headers=headers, json={"name": "A"})
    ).json()["id"]
    ws_b = (
        await client.post("/api/v1/workspaces", headers=headers, json={"name": "B"})
    ).json()["id"]

    files = {"file": ("diagram.png", _tiny_png(), "image/png")}
    await client.post(
        f"/api/v1/workspaces/{ws_a}/documents", headers=headers, files=files
    )

    res = await client.post(
        f"/api/v1/workspaces/{ws_b}/search",
        headers=headers,
        json={"query": "diagram", "limit": 5},
    )
    assert res.status_code == 200
    assert res.json() == []
