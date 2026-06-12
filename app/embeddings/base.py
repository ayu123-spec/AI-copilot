"""Embedder interface. Implementations live in embedders.py."""

from abc import ABC, abstractmethod


class Embedder(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of the vectors this embedder produces."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
