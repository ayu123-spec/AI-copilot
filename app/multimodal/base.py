"""Multimodal RAG: turn images into retrievable text.

An ``ImageDescriber`` converts image bytes into a natural-language description.
That description is then chunked, embedded, and stored exactly like any other
text, which makes images first-class, citable evidence — so a user can ask
"explain this chart" and get a grounded answer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ImageDescription:
    """A text description of an image plus provenance metadata."""

    text: str
    metadata: dict = field(default_factory=dict)


class ImageDescriber(ABC):
    """Strategy that produces a retrieval-ready text description of an image."""

    @abstractmethod
    def describe(
        self,
        image: bytes,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ImageDescription:
        """Return a description of ``image`` suitable for indexing and retrieval."""
