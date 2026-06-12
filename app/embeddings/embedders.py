"""Concrete embedders and a factory selecting one from settings.

`local` and `openai` import their heavy/optional dependencies lazily so this
module always imports cleanly. `fake` is dependency-free and deterministic,
used by tests and for offline development.
"""

import hashlib

from app.core.config import settings
from app.embeddings.base import Embedder


class FakeEmbedder(Embedder):
    """Deterministic hash-based vectors. Not meaningful, but stable and offline."""

    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self._dim
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self._dim] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class LocalEmbedder(Embedder):
    """sentence-transformers backend (default: BAAI/bge-small-en-v1.5, 384-dim)."""

    def __init__(self, model_name: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "Local embeddings need sentence-transformers. "
                "Install with: pip install -r requirements-ml.txt"
            ) from exc
        self._model = SentenceTransformer(model_name or settings.EMBEDDING_MODEL)
        self._dim = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


class OpenAIEmbedder(Embedder):
    """OpenAI embeddings (default: text-embedding-3-small, 1536-dim)."""

    def __init__(self, model_name: str = "text-embedding-3-small", dim: int = 1536):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("OpenAI backend needs: pip install openai") from exc
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = model_name
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


_cached: Embedder | None = None


def get_embedder() -> Embedder:
    """Return a singleton embedder chosen by settings.EMBEDDING_BACKEND."""
    global _cached
    if _cached is not None:
        return _cached
    backend = settings.EMBEDDING_BACKEND.lower()
    if backend == "local":
        _cached = LocalEmbedder()
    elif backend == "openai":
        _cached = OpenAIEmbedder()
    elif backend == "fake":
        _cached = FakeEmbedder()
    else:
        raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend}")
    return _cached
