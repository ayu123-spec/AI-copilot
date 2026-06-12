from app.chunking.chunkers import Chunk
from app.embeddings.embedders import FakeEmbedder
from app.rag.hybrid import HybridRetriever, reciprocal_rank_fusion
from app.vectorstore.qdrant_store import VectorStore


def test_rrf_orders_by_combined_rank():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["a", "c", "d"]])
    order = [i for i, _ in fused]
    assert order[0] == "a"  # ranked #1 in both lists
    assert order[1] == "c"  # high in both, beats b and d


def _seed_store():
    emb = FakeEmbedder(dim=64)
    store = VectorStore(collection="hybrid_test", location=":memory:")
    store.ensure_collection(emb.dimension)
    texts = [
        "the quarterly revenue grew in the cloud business",
        "cats and dogs are common household pets",
        "python is a popular programming language for data",
    ]
    chunks = [
        Chunk(text=t, metadata={"workspace_id": "ws1", "source": f"doc{i}.txt"})
        for i, t in enumerate(texts)
    ]  # chunks keep their auto-generated UUID ids (Qdrant requires UUIDs)
    store.upsert_chunks(chunks, emb.embed(texts))
    return store, emb


def test_hybrid_retrieve_surfaces_keyword_match():
    store, emb = _seed_store()
    retriever = HybridRetriever(store, emb)
    results = retriever.retrieve(
        "python programming language", where={"workspace_id": "ws1"}
    )
    assert results
    assert any("python" in r.text for r in results[:2])  # python doc near the top


def test_hybrid_retrieve_respects_tenant_filter():
    store, emb = _seed_store()
    retriever = HybridRetriever(store, emb)
    # nothing is tagged ws2, so a ws2-scoped query returns nothing
    results = retriever.retrieve("python", where={"workspace_id": "ws2"})
    assert results == []
