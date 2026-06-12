"""Run a set of evaluation cases through the retriever and aggregate metrics.

A chunk counts as 'relevant' to a case if it contains the case's expected
substring (a simple, dependency-free relevance proxy). For answer-level metrics
like faithfulness, see the optional RAGAS notes in the README.
"""

from dataclasses import dataclass
from statistics import mean

from app.evaluation.metrics import precision_at_k, recall_at_k, reciprocal_rank
from app.rag.hybrid import HybridRetriever


@dataclass
class EvalCase:
    query: str
    relevant_substring: (
        str  # a result is relevant if it contains this (case-insensitive)
    )


def _relevances(results, relevant_substring: str) -> list[bool]:
    needle = relevant_substring.lower()
    return [needle in r.text.lower() for r in results]


def evaluate_retrieval(
    retriever: HybridRetriever,
    cases: list[EvalCase],
    *,
    where: dict | None = None,
    k: int = 5,
) -> dict:
    recalls, mrrs, precisions, per_case = [], [], [], []
    for case in cases:
        results = retriever.retrieve(case.query, where=where, limit=k)
        rels = _relevances(results, case.relevant_substring)
        r, m, p = recall_at_k(rels), reciprocal_rank(rels), precision_at_k(rels)
        recalls.append(r)
        mrrs.append(m)
        precisions.append(p)
        per_case.append({"query": case.query, "hit": r, "mrr": m, "precision": p})
    return {
        "k": k,
        "num_cases": len(cases),
        "hit_rate": mean(recalls) if recalls else 0.0,
        "mrr": mean(mrrs) if mrrs else 0.0,
        "precision_at_k": mean(precisions) if precisions else 0.0,
        "per_case": per_case,
    }
