"""Qdrant vector store.

Runs three ways depending on settings:
- QDRANT_URL set        -> connect to a Qdrant server (production / docker-compose)
- otherwise             -> embedded on-disk store at QDRANT_PATH (local dev, no server)
- location=":memory:"   -> ephemeral, used by tests

`namespace` is implemented as a payload field plus a filter, giving per-workspace
isolation inside a single collection.
"""

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.chunking.chunkers import Chunk
from app.core.config import settings


@dataclass
class SearchResult:
    id: str
    score: float
    text: str
    metadata: dict


class VectorStore:
    def __init__(
        self,
        collection: str | None = None,
        location: str | None = None,
    ):
        self.collection = collection or settings.QDRANT_COLLECTION
        if location == ":memory:":
            self.client = QdrantClient(location=":memory:")
        elif settings.QDRANT_URL:
            self.client = QdrantClient(url=settings.QDRANT_URL)
        else:
            self.client = QdrantClient(path=settings.QDRANT_PATH)

    def ensure_collection(self, dim: int) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        points = [
            PointStruct(
                id=chunk.id, vector=vec, payload={**chunk.metadata, "text": chunk.text}
            )
            for chunk, vec in zip(chunks, vectors, strict=False)
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def upsert_records(
        self,
        records: list[tuple[str, str, dict]],
        vectors: list[list[float]],
    ) -> int:
        """Upsert arbitrary ``(id, text, metadata)`` records — used for long-term
        memories. Mirrors :meth:`upsert_chunks` without depending on the chunking
        layer; the id lets a record be updated or deleted later."""
        points = [
            PointStruct(id=rec_id, vector=vec, payload={**meta, "text": text})
            for (rec_id, text, meta), vec in zip(records, vectors, strict=False)
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    @staticmethod
    def _filter(must: dict | None) -> Filter | None:
        if not must:
            return None
        return Filter(
            must=[
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in must.items()
            ]
        )

    def search(
        self, vector: list[float], limit: int = 5, where: dict | None = None
    ) -> list[SearchResult]:
        if not self.client.collection_exists(self.collection):
            return []
        hits = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            query_filter=self._filter(where),
            with_payload=True,
        ).points
        results = []
        for h in hits:
            payload = dict(h.payload or {})
            text = payload.pop("text", "")
            results.append(
                SearchResult(id=str(h.id), score=h.score, text=text, metadata=payload)
            )
        return results

    def fetch_all(
        self, where: dict | None = None, batch: int = 256
    ) -> list[SearchResult]:
        """Page through every stored chunk matching `where`. Used to build the
        BM25 index for hybrid search, so it must carry the same tenant filter."""
        if not self.client.collection_exists(self.collection):
            return []
        results: list[SearchResult] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=self._filter(where),
                limit=batch,
                offset=offset,
                with_payload=True,
            )
            for p in points:
                payload = dict(p.payload or {})
                text = payload.pop("text", "")
                results.append(
                    SearchResult(id=str(p.id), score=0.0, text=text, metadata=payload)
                )
            if offset is None:
                break
        return results

    def delete_by_document(self, document_id: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=self._filter({"document_id": document_id}),
        )
