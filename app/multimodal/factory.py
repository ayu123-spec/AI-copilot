"""Selects the image describer configured by settings."""

from app.core.config import settings
from app.multimodal.base import ImageDescriber
from app.multimodal.describers import FakeImageDescriber

_describer: ImageDescriber | None = None


def get_image_describer() -> ImageDescriber:
    """Process-wide singleton describer chosen by ``IMAGE_DESCRIBER_BACKEND``.

    Defaults to the deterministic fake so local dev and tests need no vision API.
    """
    global _describer
    if _describer is None:
        backend = settings.IMAGE_DESCRIBER_BACKEND.lower()
        if backend in ("anthropic", "vision", "llm"):
            from app.multimodal.describers import LLMImageDescriber

            _describer = LLMImageDescriber()
        else:
            _describer = FakeImageDescriber()
    return _describer
