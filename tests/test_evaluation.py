from app.chunking.chunkers import Chunk
from app.embeddings.embedders import FakeEmbedder
from app.evaluation.harness import EvalCase, evaluate_retrieval
from app.evaluation.metrics import precision_at_k, recall_at_k, reciprocal_rank
from app.rag.hybrid import HybridRetriever
from app.vectorstore.qdrant_store import VectorStore


def test_metric_functions():
    assert recall_at_k([False, True, False]) == 1.0
    assert recall_at_k([False, False]) == 0.0
    assert reciprocal_rank([False, True, False]) == 0.5
    assert reciprocal_rank([True]) == 1.0
    assert precision_at_k([True, False, True, False]) == 0.5
    assert precision_at_k([]) == 0.0


def test_evaluate_retrieval_runs_and_scores():
    emb = FakeEmbedder(dim=64)
    store = VectorStore(collection="eval_test", location=":memory:")
    store.ensure_collection(emb.dimension)
    texts = {
        "a": "quarterly revenue grew twenty percent",
        "b": "employees get twenty five vacation days",
        "c": "data is encrypted using strong cryptography",
    }
    chunks = [
        Chunk(text=t, metadata={"source": k, "workspace_id": "w"})
        for k, t in texts.items()
    ]
    store.upsert_chunks(chunks, emb.embed(list(texts.values())))

    retriever = HybridRetriever(store, emb)
    cases = [
        EvalCase("how much revenue growth", "revenue grew"),
        EvalCase("vacation days policy", "vacation days"),
    ]
    m = evaluate_retrieval(retriever, cases, where={"workspace_id": "w"}, k=3)
    assert m["num_cases"] == 2
    assert 0.0 <= m["hit_rate"] <= 1.0
    assert 0.0 <= m["mrr"] <= 1.0
    assert 0.0 <= m["precision_at_k"] <= 1.0
    assert m["hit_rate"] == 1.0  # the relevant docs are in the small candidate set
