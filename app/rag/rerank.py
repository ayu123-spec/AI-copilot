"""Re-ranking: re-score retrieved chunks against the query for final precision.

Hybrid search casts a wide, cheap net; a cross-encoder then reads each (query,
chunk) pair together and scores true relevance, which is far more accurate than
the first-stage scores. We keep the wide candidate set small (e.g. top 20) and
re-rank down to the few chunks the model actually sees (e.g. top 5).

`cross_encoder` uses sentence-transformers (lazy-imported). `fake` is a
dependency-free lexical re-ranker for offline use and tests.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import replace

from app.core.config import settings
from app.rag.hybrid import RetrievedChunk


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class Reranker(ABC):
    @abstractmethod
    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_n: int = 5
    ) -> list[RetrievedChunk]: ...


class FakeReranker(Reranker):
    """Scores by shared-token overlap. Deterministic, offline, used by tests."""

    def rerank(self, query, chunks, top_n=5):
        q = _tokens(query)
        scored = [(len(q & _tokens(c.text)), c) for c in chunks]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [replace(c, score=float(s)) for s, c in scored[:top_n]]


class CrossEncoderReranker(Reranker):
    """Neural cross-encoder (default ms-marco-MiniLM). Needs requirements-ml.txt."""

    def __init__(self, model_name: str | None = None):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "Cross-encoder re-ranking needs sentence-transformers. "
                "Install with: pip install -r requirements-ml.txt"
            ) from exc
        self._model = CrossEncoder(model_name or settings.RERANK_MODEL)

    def rerank(self, query, chunks, top_n=5):
        if not chunks:
            return []
        scores = self._model.predict([(query, c.text) for c in chunks])
        ranked = sorted(
            zip(scores, chunks, strict=False), key=lambda sc: sc[0], reverse=True
        )
        return [replace(c, score=float(s)) for s, c in ranked[:top_n]]


def get_reranker(backend: str | None = None) -> Reranker:
    """Build a reranker from settings. The RAG engine constructs this once and
    reuses it, so a heavy cross-encoder model loads only a single time."""
    backend = (backend or settings.RERANK_BACKEND).lower()
    if backend == "cross_encoder":
        return CrossEncoderReranker()
    if backend == "fake":
        return FakeReranker()
    raise ValueError(f"Unknown RERANK_BACKEND: {backend}")
