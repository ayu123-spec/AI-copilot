"""Sparse retrieval over chunk text using BM25.

BM25 ranks documents by exact term overlap (good at names, codes, rare words),
complementing dense vector search (good at meaning). We build the index over a
list of candidate chunks; in the pipeline those come from the workspace's stored
chunks, so it stays tenant-scoped.
"""

import re
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class SparseHit:
    id: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)


class BM25Index:
    """In-memory BM25 index over a list of {id, text, metadata} dicts."""

    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._bm25 = BM25Okapi([_tokenize(d["text"]) for d in docs]) if docs else None

    def search(self, query: str, limit: int = 5) -> list[SparseHit]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(
            zip(self._docs, scores, strict=False), key=lambda ds: ds[1], reverse=True
        )
        return [
            SparseHit(
                id=d["id"],
                score=float(s),
                text=d["text"],
                metadata=d.get("metadata", {}),
            )
            for d, s in ranked[:limit]
        ]
