"""Core agent contracts.

This defines the situation an agent runs in (:class:`AgentContext`), the
step-by-step trace it produces (:class:`AgentStep` / :class:`AgentRun`), and the
:class:`Agent` base class itself.

Agents are *synchronous*, matching the RAG compute layer. Anything that touches
the database — loading conversation history, retrieving long-term memory,
persisting a run — happens in the async service/API layer and is handed to the
agent via :class:`AgentContext`. Citations reuse the single
:class:`app.rag.engine.Citation` type so the whole system speaks one citation
format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.rag.engine import Citation


@dataclass
class AgentContext:
    """Everything an agent needs to know about the caller and situation.

    Tenancy (``organization_id`` / ``workspace_id``) is carried explicitly so
    tools can scope their work and never leak across tenants. ``history`` and
    ``memories`` are populated by the service layer; short- and long-term memory
    are wired in a later part.
    """

    organization_id: str | None = None
    workspace_id: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStep:
    """One iteration of an agent's reasoning loop — a ReAct-style trace entry of
    *thought -> chosen tool + input -> observation*. Any field may be absent
    (e.g. a pure reasoning step has no tool)."""

    thought: str | None = None
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    observation: str | None = None


@dataclass
class AgentRun:
    """The full result of running an agent: the final answer, the citations it
    relied on, and the ordered trace of steps that produced it. The trace makes
    every run inspectable and (later) persistable."""

    query: str
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """A named, described unit that turns a query into a cited :class:`AgentRun`.

    Concrete agents set :attr:`name` and :attr:`description` and implement
    :meth:`run`.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        """Run the agent on ``query`` and return its result."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Agent {self.name!r}>"
