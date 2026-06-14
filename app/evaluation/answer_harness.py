"""End-to-end answer evaluation harness.

Given an ``answer_fn`` (anything that maps a query to an answer + the contexts it
used + its citations), this runs the regression cases and aggregates retrieval and
answer-quality metrics, latency, and an estimated token cost into one report.

The harness is decoupled from any particular pipeline: tests pass a controlled
``answer_fn``; ``run_full.py`` passes one backed by the configured LLM.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import mean
from time import perf_counter

from app.evaluation.answer_metrics import (
    answer_relevance,
    citation_accuracy,
    faithfulness,
    hallucination_rate,
)
from app.evaluation.metrics import precision_at_k, recall_at_k, reciprocal_rank


@dataclass
class AnswerOutput:
    """What an answer function returns for a single query."""

    answer: str
    contexts: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


AnswerFn = Callable[[str], AnswerOutput]


@dataclass
class EvalCaseQA:
    query: str
    relevant_substring: str  # a context is relevant if it contains this
    reference_answer: str = ""


@dataclass
class CaseResult:
    query: str
    faithfulness: float
    hallucination_rate: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    reciprocal_rank: float
    citation_accuracy: float
    latency_ms: float
    tokens: int


@dataclass
class EvalReport:
    n: int
    faithfulness: float
    hallucination_rate: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    mrr: float
    citation_accuracy: float
    avg_latency_ms: float
    total_tokens: int
    est_cost_usd: float
    per_case: list[CaseResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        rows = [
            ("Faithfulness", f"{self.faithfulness:.3f}"),
            ("Hallucination rate", f"{self.hallucination_rate:.3f}"),
            ("Answer relevance", f"{self.answer_relevance:.3f}"),
            ("Context precision@k", f"{self.context_precision:.3f}"),
            ("Context recall@k", f"{self.context_recall:.3f}"),
            ("MRR", f"{self.mrr:.3f}"),
            ("Citation accuracy", f"{self.citation_accuracy:.3f}"),
            ("Avg latency (ms)", f"{self.avg_latency_ms:.1f}"),
            ("Total tokens", str(self.total_tokens)),
            ("Est. cost (USD)", f"{self.est_cost_usd:.6f}"),
        ]
        lines = [
            f"### Evaluation report ({self.n} cases)",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]
        return "\n".join(lines)


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def evaluate_answers(
    answer_fn: AnswerFn,
    cases: list[EvalCaseQA],
    *,
    cost_per_1k_tokens: float = 0.003,
) -> EvalReport:
    """Run all cases through ``answer_fn`` and aggregate the metrics."""
    results: list[CaseResult] = []
    for case in cases:
        start = perf_counter()
        out = answer_fn(case.query)
        latency_ms = (perf_counter() - start) * 1000.0

        needle = case.relevant_substring.lower()
        relevances = [needle in c.lower() for c in out.contexts]
        tokens = _approx_tokens(out.answer) + sum(
            _approx_tokens(c) for c in out.contexts
        )

        results.append(
            CaseResult(
                query=case.query,
                faithfulness=faithfulness(out.answer, out.contexts),
                hallucination_rate=hallucination_rate(out.answer, out.contexts),
                answer_relevance=answer_relevance(out.answer, case.query),
                context_precision=precision_at_k(relevances),
                context_recall=recall_at_k(relevances),
                reciprocal_rank=reciprocal_rank(relevances),
                citation_accuracy=citation_accuracy(out.citations, out.contexts),
                latency_ms=latency_ms,
                tokens=tokens,
            )
        )

    def agg(attr: str) -> float:
        return round(mean(getattr(r, attr) for r in results), 6) if results else 0.0

    total_tokens = sum(r.tokens for r in results)
    return EvalReport(
        n=len(results),
        faithfulness=agg("faithfulness"),
        hallucination_rate=agg("hallucination_rate"),
        answer_relevance=agg("answer_relevance"),
        context_precision=agg("context_precision"),
        context_recall=agg("context_recall"),
        mrr=agg("reciprocal_rank"),
        citation_accuracy=agg("citation_accuracy"),
        avg_latency_ms=round(agg("latency_ms"), 3),
        total_tokens=total_tokens,
        est_cost_usd=round(total_tokens / 1000 * cost_per_1k_tokens, 6),
        per_case=results,
    )
