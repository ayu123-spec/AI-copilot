from app.chunking.chunkers import Chunk
from app.embeddings.embedders import FakeEmbedder
from app.vectorstore.qdrant_store import VectorStore


def test_fake_embedder_dimension_and_determinism():
    emb = FakeEmbedder(dim=128)
    a = emb.embed(["hello world"])
    b = emb.embed(["hello world"])
    assert len(a[0]) == 128
    assert a == b  # deterministic
    assert emb.dimension == 128


def test_vector_store_upsert_and_search():
    emb = FakeEmbedder(dim=64)
    store = VectorStore(collection="t1", location=":memory:")
    store.ensure_collection(emb.dimension)

    texts = ["cats are mammals", "dogs are mammals", "python is a language"]
    chunks = [Chunk(text=t, metadata={"document_id": "d1", "chunk_index": i}) for i, t in enumerate(texts)]
    store.upsert_chunks(chunks, emb.embed(texts))

    results = store.search(emb.embed_query("python language"), limit=2)
    assert len(results) == 2
    assert any("python" in r.text for r in results)


def test_vector_store_metadata_filter_isolation():
    emb = FakeEmbedder(dim=64)
    store = VectorStore(collection="t2", location=":memory:")
    store.ensure_collection(emb.dimension)

    a = [Chunk(text="alpha doc text", metadata={"workspace_id": "wsA"})]
    b = [Chunk(text="bravo doc text", metadata={"workspace_id": "wsB"})]
    store.upsert_chunks(a, emb.embed([a[0].text]))
    store.upsert_chunks(b, emb.embed([b[0].text]))

    only_a = store.search(emb.embed_query("doc text"), limit=10, where={"workspace_id": "wsA"})
    assert only_a
    assert all(r.metadata.get("workspace_id") == "wsA" for r in only_a)


def test_vector_store_delete_by_document():
    emb = FakeEmbedder(dim=64)
    store = VectorStore(collection="t3", location=":memory:")
    store.ensure_collection(emb.dimension)
    chunks = [Chunk(text="to be deleted", metadata={"document_id": "doc-x"})]
    store.upsert_chunks(chunks, emb.embed([chunks[0].text]))

    store.delete_by_document("doc-x")
    results = store.search(emb.embed_query("deleted"), limit=10, where={"document_id": "doc-x"})
    assert results == []
