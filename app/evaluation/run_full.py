"""Run the end-to-end answer evaluation and print a report.

    python -m app.evaluation.run_full

This isolates *generation* quality: each question is answered using its gold
context (so it does not depend on retrieval), with the configured LLM backend.
With the default 'fake' backend the numbers are illustrative; set
LLM_BACKEND=anthropic (+ ANTHROPIC_API_KEY) for meaningful, publishable numbers.
"""

from app.core.config import settings
from app.evaluation.answer_harness import AnswerOutput, evaluate_answers
from app.evaluation.answer_metrics import _token_set
from app.evaluation.dataset import CORPUS, REGRESSION_CASES

SYSTEM_PROMPT = (
    "Answer the question using only the provided context. "
    "Be concise and do not invent facts."
)


def _make_generator():
    backend = settings.LLM_BACKEND.lower()
    if backend == "anthropic":
        from app.rag.llm import AnthropicGenerator

        return AnthropicGenerator()
    if backend == "openai":
        from app.rag.llm import OpenAIGenerator

        return OpenAIGenerator()
    from app.rag.llm import FakeGenerator

    return FakeGenerator()


def _best_context(query: str) -> tuple[str, str]:
    """Pick the corpus doc that shares the most content tokens with the query."""
    q = _token_set(query)
    best_name, best_text, best_score = "", "", -1
    for name, text in CORPUS.items():
        score = len(q & _token_set(text))
        if score > best_score:
            best_name, best_text, best_score = name, text, score
    return best_name, best_text


def build_answer_fn():
    generator = _make_generator()

    def answer_fn(query: str) -> AnswerOutput:
        source, context = _best_context(query)
        user = f"Context:\n{context}\n\nQuestion: {query}"
        answer = generator.generate(SYSTEM_PROMPT, user)
        return AnswerOutput(answer=answer, contexts=[context], citations=[source])

    return answer_fn


def main() -> None:
    report = evaluate_answers(build_answer_fn(), REGRESSION_CASES)
    print(report.to_markdown())
    print(f"\nLLM backend: {settings.LLM_BACKEND}")
    if settings.LLM_BACKEND.lower() == "fake":
        print(
            "Note: 'fake' backend — numbers are illustrative. "
            "Set LLM_BACKEND=anthropic for meaningful results."
        )


if __name__ == "__main__":
    main()
