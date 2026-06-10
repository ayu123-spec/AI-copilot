"""Retrieval evaluation metrics. Pure functions, no LLM required.

Each takes a list of booleans — whether each retrieved result (in rank order)
is relevant to the query — and returns a score.
"""


def recall_at_k(relevances: list[bool]) -> float:
    """1.0 if any top-k result is relevant, else 0.0 (a.k.a. hit rate)."""
    return 1.0 if any(relevances) else 0.0


def reciprocal_rank(relevances: list[bool]) -> float:
    """1 / rank of the first relevant result (rank is 1-based); 0.0 if none."""
    for rank, relevant in enumerate(relevances, start=1):
        if relevant:
            return 1.0 / rank
    return 0.0


def precision_at_k(relevances: list[bool]) -> float:
    """Fraction of the top-k results that are relevant."""
    return sum(relevances) / len(relevances) if relevances else 0.0
