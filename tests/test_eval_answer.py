"""Tests for the answer-evaluation framework (Module 15). Pure and offline."""

from app.evaluation.answer_harness import AnswerOutput, EvalCaseQA, evaluate_answers
from app.evaluation.answer_metrics import (
    answer_relevance,
    citation_accuracy,
    faithfulness,
    hallucination_rate,
)


def test_faithfulness_distinguishes_grounded_from_hallucinated():
    contexts = ["The sky is blue and the grass is green in summer."]
    grounded = "The sky is blue. The grass is green."
    hallucinated = "The sky is purple and dragons rule the kingdom."

    assert faithfulness(grounded, contexts) == 1.0
    assert faithfulness(hallucinated, contexts) < 0.5
    assert hallucination_rate(hallucinated, contexts) > 0.5
    # An empty answer makes no claims, so it cannot hallucinate.
    assert faithfulness("", contexts) == 1.0


def test_answer_relevance():
    assert (
        answer_relevance("Revenue grew twenty percent", "How much did revenue grow?")
        > 0.0
    )
    assert answer_relevance("totally unrelated content", "encryption at rest") == 0.0
    assert answer_relevance("", "some question tokens") == 0.0


def test_citation_accuracy():
    contexts = ["All customer data is encrypted at rest using AES-256."]
    assert citation_accuracy(["AES-256 encryption"], contexts) == 1.0
    assert citation_accuracy(["unrelated zzz token"], contexts) == 0.0
    assert citation_accuracy([], contexts) == 1.0  # nothing incorrect claimed


def test_evaluate_answers_aggregates_report():
    cases = [
        EvalCaseQA(
            query="How much did revenue grow?",
            relevant_substring="20 percent",
            reference_answer="Revenue grew 20 percent.",
        )
    ]

    def answer_fn(query: str) -> AnswerOutput:
        return AnswerOutput(
            answer="Revenue grew 20 percent driven by cloud services.",
            contexts=["Quarterly revenue grew 20 percent driven by cloud services."],
            citations=["revenue 20 percent"],
        )

    report = evaluate_answers(answer_fn, cases)

    assert report.n == 1
    assert report.context_recall == 1.0  # "20 percent" is in the context
    assert report.faithfulness == 1.0  # answer fully grounded
    assert report.hallucination_rate == 0.0
    assert report.total_tokens > 0
    assert "Faithfulness" in report.to_markdown()


def test_evaluate_answers_flags_ungrounded_answer():
    cases = [EvalCaseQA(query="What is encrypted?", relevant_substring="AES-256")]

    def answer_fn(query: str) -> AnswerOutput:
        return AnswerOutput(
            answer="The mreowing flubber wibbles across the zorptastic meadow.",
            contexts=["All customer data is encrypted at rest using AES-256."],
            citations=[],
        )

    report = evaluate_answers(answer_fn, cases)
    assert report.faithfulness < 0.5
    assert report.hallucination_rate > 0.5
