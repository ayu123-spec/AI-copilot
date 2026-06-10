"""Hybrid retrieval: dense (Qdrant vectors) + sparse (BM25), fused with RRF.

Reciprocal Rank Fusion combines two ranked lists by position rather than raw
score, so the two retrievers' incomparable scores don't need normalizing. A chunk
ranked highly by *either* method, and especially by *both*, rises to the top.
"""
from dataclasses import dataclass, field

from app.embeddings.base import Embedder
from app.rag.sparse import BM25Index
from app.vectorstore.qdrant_store import VectorStore


@dataclass
class RetrievedChunk:
    id: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse ranked id-lists. Returns (id, score) sorted best-first."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, _id in enumerate(ranking, start=1):
            scores[_id] = scores.get(_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class HybridRetriever:
    def __init__(self, store: VectorStore, embedder: Embedder, k: int = 60):
        self.store = store
        self.embedder = embedder
        self.k = k

    def retrieve(
        self,
        query: str,
        *,
        where: dict | None = None,
        dense_k: int = 20,
        sparse_k: int = 20,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        dense = self.store.search(self.embedder.embed_query(query), limit=dense_k, where=where)

        corpus = self.store.fetch_all(where=where)
        bm25 = BM25Index(
            [{"id": c.id, "text": c.text, "metadata": c.metadata} for c in corpus]
        )
        sparse = bm25.search(query, limit=sparse_k)

        # Keep text/metadata for every id we saw, so we can rebuild full results.
        registry: dict[str, tuple[str, dict]] = {}
        for r in dense:
            registry[r.id] = (r.text, r.metadata)
        for r in sparse:
            registry.setdefault(r.id, (r.text, r.metadata))

        fused = reciprocal_rank_fusion(
            [[r.id for r in dense], [r.id for r in sparse]], k=self.k
        )
        out = []
        for _id, score in fused[:limit]:
            text, meta = registry[_id]
            out.append(RetrievedChunk(id=_id, score=score, text=text, metadata=meta))
        return out
