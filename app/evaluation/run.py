"""Run retrieval evaluation on a small built-in corpus and print the metrics.

    python -m app.evaluation.run

Numbers are only meaningful with a real embedding backend (set EMBEDDING_BACKEND
to 'local' or 'openai'). With the default 'fake' backend they are illustrative.
"""

from app.chunking.chunkers import Chunk
from app.embeddings.embedders import get_embedder
from app.evaluation.harness import EvalCase, evaluate_retrieval
from app.rag.hybrid import HybridRetriever
from app.vectorstore.qdrant_store import VectorStore

CORPUS = {
    "finance.txt": (
        "The company reported that quarterly revenue grew 20 percent, "
        "driven by cloud services and enterprise subscriptions."
    ),
    "hr.txt": (
        "Employees are entitled to 25 days of paid annual leave and "
        "flexible remote working arrangements."
    ),
    "security.txt": (
        "All customer data is encrypted at rest using AES-256 and "
        "access requires multi-factor authentication."
    ),
    "product.txt": (
        "The product roadmap prioritizes a mobile app, offline sync, "
        "and a public API for integrations."
    ),
}

CASES = [
    EvalCase("How much did revenue grow last quarter?", "revenue grew 20 percent"),
    EvalCase(
        "How many vacation days do employees get?", "25 days of paid annual leave"
    ),
    EvalCase("How is customer data protected?", "encrypted at rest"),
    EvalCase("What is on the product roadmap?", "product roadmap"),
]


def main() -> None:
    embedder = get_embedder()
    store = VectorStore(collection="eval", location=":memory:")
    store.ensure_collection(embedder.dimension)
    chunks = [
        Chunk(text=t, metadata={"source": s, "workspace_id": "eval"})
        for s, t in CORPUS.items()
    ]
    store.upsert_chunks(chunks, embedder.embed([c.text for c in chunks]))

    retriever = HybridRetriever(store, embedder)
    m = evaluate_retrieval(retriever, CASES, where={"workspace_id": "eval"}, k=3)

    print(
        f"\nRetrieval evaluation  (embedder={embedder.__class__.__name__}, "
        f"k={m['k']}, cases={m['num_cases']})"
    )
    print("-" * 58)
    print(f"  Hit rate      : {m['hit_rate']:.2f}")
    print(f"  MRR           : {m['mrr']:.2f}")
    print(f"  Precision@k   : {m['precision_at_k']:.2f}")
    print("-" * 58)
    for row in m["per_case"]:
        print(f"  [{'HIT ' if row['hit'] else 'MISS'}] {row['query']}")
    print()


if __name__ == "__main__":
    main()
