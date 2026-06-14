"""Multimodal RAG package: image understanding for retrieval."""

from app.multimodal.base import ImageDescriber, ImageDescription
from app.multimodal.describers import FakeImageDescriber
from app.multimodal.factory import get_image_describer

__all__ = [
    "ImageDescriber",
    "ImageDescription",
    "FakeImageDescriber",
    "get_image_describer",
]
