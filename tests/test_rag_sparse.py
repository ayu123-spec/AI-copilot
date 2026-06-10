from app.rag.sparse import BM25Index

DOCS = [
    {"id": "1", "text": "cats and dogs are common household pets", "metadata": {"source": "a"}},
    {"id": "2", "text": "python is a popular programming language", "metadata": {"source": "b"}},
    {"id": "3", "text": "revenue grew strongly in the cloud business", "metadata": {"source": "c"}},
]


def test_bm25_ranks_relevant_first():
    idx = BM25Index(DOCS)
    hits = idx.search("python programming", limit=2)
    assert hits
    assert hits[0].id == "2"
    assert hits[0].metadata["source"] == "b"


def test_bm25_empty_corpus_returns_nothing():
    assert BM25Index([]).search("anything") == []
