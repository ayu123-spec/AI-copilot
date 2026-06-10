"""Answer generation — the LLM step of RAG.

Pluggable backends: 'anthropic' (Claude), 'openai', or 'fake' (offline/tests).
The real SDKs are imported lazily, so this module always imports even if neither
is installed. Install the one you want: `pip install anthropic` or `pip install
openai`, set the matching key, and set LLM_BACKEND.
"""
from abc import ABC, abstractmethod

from app.core.config import settings


class Generator(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        ...


class FakeGenerator(Generator):
    """Deterministic, offline. Returns a templated grounded answer so the full
    RAG flow (retrieve -> rerank -> context -> answer) can be tested without keys."""

    def generate(self, system: str, user: str) -> str:
        return "Based on the provided sources [1], here is a grounded answer."


class AnthropicGenerator(Generator):
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, model_name: str | None = None):
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("Anthropic backend needs: pip install anthropic") from exc
        self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = model_name or self.DEFAULT_MODEL

    def generate(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")


class OpenAIGenerator(Generator):
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model_name: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("OpenAI backend needs: pip install openai") from exc
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = model_name or self.DEFAULT_MODEL

    def generate(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


def get_generator(backend: str | None = None) -> Generator:
    backend = (backend or settings.LLM_BACKEND).lower()
    model = settings.LLM_MODEL or None
    if backend == "anthropic":
        return AnthropicGenerator(model)
    if backend == "openai":
        return OpenAIGenerator(model)
    if backend == "fake":
        return FakeGenerator()
    raise ValueError(f"Unknown LLM_BACKEND: {backend}")
