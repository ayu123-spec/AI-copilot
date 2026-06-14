"""Concrete image describers.

``FakeImageDescriber`` is deterministic and dependency-free for offline tests and
local development. ``LLMImageDescriber`` calls a vision-capable model and is
imported lazily so this module never hard-depends on the SDK or the network.
"""

import hashlib
from pathlib import Path

from app.core.logging import get_logger
from app.multimodal.base import ImageDescriber, ImageDescription

logger = get_logger(__name__)


def _subject_from_filename(filename: str | None) -> str:
    if not filename:
        return "image"
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem or "image"


class FakeImageDescriber(ImageDescriber):
    """Deterministic describer used offline.

    It does not inspect pixels; it derives a stable caption from the file name
    and a content hash, so the full ingestion path (describe -> chunk -> embed ->
    store -> retrieve) is exercised without a vision model or network access.
    """

    def describe(
        self,
        image: bytes,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ImageDescription:
        fingerprint = hashlib.sha256(image or b"").hexdigest()[:8]
        subject = _subject_from_filename(filename)
        text = (
            f"Figure: {subject}. This image appears to contain a chart or diagram "
            f"with labelled axes, one or more data series, and a legend. "
            f"Visual fingerprint {fingerprint}."
        )
        return ImageDescription(
            text=text,
            metadata={
                "modality": "image",
                "describer": "fake",
                "fingerprint": fingerprint,
                "content_type": content_type,
            },
        )


class LLMImageDescriber(ImageDescriber):  # pragma: no cover - needs a vision API
    """Describes images with a vision-capable Anthropic model."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        from app.core.config import settings

        self._model = model or settings.VISION_MODEL
        self._api_key = api_key or settings.ANTHROPIC_API_KEY

    def describe(
        self,
        image: bytes,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ImageDescription:
        import base64

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        media_type = content_type or "image/png"
        message = client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image).decode("utf-8"),
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this image in detail for document "
                                "retrieval. Transcribe any text, report chart "
                                "values and axis labels, and summarise structure."
                            ),
                        },
                    ],
                }
            ],
        )
        text = "".join(
            b.text for b in message.content if getattr(b, "type", "") == "text"
        )
        return ImageDescription(
            text=text,
            metadata={
                "modality": "image",
                "describer": "anthropic",
                "model": self._model,
            },
        )
