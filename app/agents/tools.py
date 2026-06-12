"""Tools an agent can invoke.

A :class:`Tool` is a named, described, uniform capability that takes keyword
arguments and returns a structured :class:`ToolResult`. Tools are *synchronous*,
matching the rest of the RAG/agent compute layer (retrieval, re-ranking,
generation). Anything that needs the database runs in the async service/API
layer and is passed into a tool as plain data.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class ToolError(Exception):
    """Raised when a tool cannot complete its work."""


@dataclass
class ToolResult:
    """The outcome of a single tool invocation.

    ``output`` is the human/LLM-readable text that flows back into the agent's
    reasoning. ``metadata`` carries any structured payload (rows, ids, scores)
    that the caller or a later step may want.
    """

    output: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """A named capability an agent can call.

    Concrete tools set :attr:`name` and :attr:`description` (the description
    tells the agent — or an LLM choosing tools — when to use it) and implement
    :meth:`run`.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool and return its result."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Tool {self.name!r}>"


class FunctionTool(Tool):
    """Adapt a plain callable into a :class:`Tool`.

    Saves a dedicated class for simple capabilities. The wrapped callable may
    return either a string (wrapped into a :class:`ToolResult`) or a
    :class:`ToolResult` directly. Any exception it raises is normalised to a
    :class:`ToolError` so agents handle failures uniformly.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self._func = func

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._func(**kwargs)
        except ToolError:
            raise
        except Exception as exc:  # normalise any failure
            raise ToolError(str(exc)) from exc
        if isinstance(result, ToolResult):
            return result
        return ToolResult(output=str(result))
