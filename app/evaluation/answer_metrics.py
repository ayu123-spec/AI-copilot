"""Answer-level evaluation metrics.

These complement the retrieval metrics in ``metrics.py`` by scoring the *generated
answer* against the retrieved context. They are deterministic, pure, and offline:
no LLM or network is required, so they run in CI on every change. An optional
``LLMJudge`` (lazy-imported, opt-in) is provided for those who want LLM-graded
faithfulness in the spirit of RAGAS/DeepEval.

The heuristics use content-token overlap. They are intentionally simple and
explainable; for production-grade judging, enable the LLM backend.
"""

import re
from statistics import mean

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "to",
    "of",
    "in",
    "on",
    "at",
    "for",
    "with",
    "by",
    "from",
    "as",
    "that",
    "this",
    "these",
    "those",
    "it",
    "its",
    "he",
    "she",
    "they",
    "we",
    "you",
    "i",
    "his",
    "her",
    "their",
    "our",
    "your",
    "my",
    "has",
    "have",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "can",
    "could",
    "should",
    "may",
    "might",
    "must",
    "not",
    "no",
    "so",
    "if",
    "then",
    "than",
    "there",
    "here",
    "what",
    "which",
    "who",
    "whom",
    "how",
    "when",
    "where",
    "why",
    "into",
    "over",
    "about",
    "per",
    "via",
    "using",
    "use",
    "used",
}


def _tokens(text: str) -> list[str]:
    return [
        t for t in _WORD.findall(text.lower()) if t not in _STOPWORDS and len(t) > 2
    ]


def _token_set(text: str) -> set[str]:
    return set(_tokens(text))


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def faithfulness(answer: str, contexts: list[str], *, threshold: float = 0.6) -> float:
    """Fraction of the answer's claims that are grounded in the context.

    Each answer sentence is "supported" when at least ``threshold`` of its content
    tokens appear in the combined context. Returns 1.0 for an answer that makes no
    verifiable claims (e.g. an empty answer or a pure refusal).
    """
    context_tokens: set[str] = set()
    for c in contexts:
        context_tokens |= _token_set(c)

    supported = []
    for sentence in _sentences(answer):
        toks = _token_set(sentence)
        if not toks:
            supported.append(1.0)  # no claim to verify
            continue
        overlap = len(toks & context_tokens) / len(toks)
        supported.append(1.0 if overlap >= threshold else 0.0)
    return mean(supported) if supported else 1.0


def hallucination_rate(answer: str, contexts: list[str]) -> float:
    """Fraction of answer claims NOT grounded in the context (1 - faithfulness)."""
    return round(1.0 - faithfulness(answer, contexts), 6)


def answer_relevance(answer: str, query: str) -> float:
    """How much of the question's content the answer actually addresses (0..1)."""
    q = _token_set(query)
    if not q:
        return 1.0
    return len(q & _token_set(answer)) / len(q)


def citation_accuracy(
    citations: list[str], contexts: list[str], *, threshold: float = 0.3
) -> float:
    """Fraction of citations whose text is actually backed by a retrieved context.

    Returns 1.0 when there are no citations (nothing incorrect was claimed).
    """
    if not citations:
        return 1.0
    context_token_sets = [_token_set(c) for c in contexts]

    def supported(citation: str) -> bool:
        ct = _token_set(citation)
        if not ct:
            return False
        return any(len(ct & cs) / len(ct) >= threshold for cs in context_token_sets)

    return mean(1.0 if supported(c) else 0.0 for c in citations)


class LLMJudge:  # pragma: no cover - requires a real LLM
    """Optional LLM-graded faithfulness (opt-in), in the spirit of RAGAS/DeepEval."""

    def __init__(self, generator=None):
        if generator is None:
            from app.rag.llm import AnthropicGenerator

            generator = AnthropicGenerator()
        self._generator = generator

    def faithfulness(self, answer: str, contexts: list[str]) -> float:
        context = "\n\n".join(contexts)
        verdicts = []
        for sentence in _sentences(answer):
            prompt = (
                "Context:\n"
                f"{context}\n\n"
                f'Claim: "{sentence}"\n\n'
                "Is the claim fully supported by the context? Answer yes or no."
            )
            reply = self._generator.generate(
                "You are a strict fact-checker. Reply with only 'yes' or 'no'.",
                prompt,
            )
            verdicts.append(1.0 if reply.strip().lower().startswith("y") else 0.0)
        return mean(verdicts) if verdicts else 1.0
