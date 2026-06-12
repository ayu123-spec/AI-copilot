"""LangGraph orchestration: route a query to the right agent, then run it.

A small ``StateGraph`` classifies the query in a ``route`` node, then a
conditional edge dispatches to the chosen agent's node. Routing is pluggable:
:func:`keyword_router` is deterministic and offline (the default, so the graph
works with no LLM), while :func:`make_llm_router` asks the generator to choose
among the registered agents for real deployments.
"""

import re
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.base import AgentContext, AgentRun
from app.agents.registry import AgentRegistry
from app.rag.llm import Generator

#: A router maps a query string to the name of the agent that should handle it.
Router = Callable[[str], str]

# Whole-word signals that a question is quantitative/tabular (matched as words,
# so "sum" does not fire on "summarise").
_SQL_WORDS = {
    "average", "total", "totals", "sum", "count", "counts", "revenue", "unit",
    "units", "sale", "sales", "quarter", "quarters", "region", "regions",
    "product", "products", "highest", "lowest", "trend", "trends", "compare",
    "most", "least", "rank", "ranking",
}  # fmt: skip
_SQL_PHRASES = ("how many", "number of", "per region", "per product", "per quarter")


def keyword_router(query: str) -> str:
    """Deterministic default: quantitative/tabular questions route to ``sql``,
    everything else to ``research``."""
    q = query.lower()
    words = set(re.findall(r"[a-z]+", q))
    if words & _SQL_WORDS or any(phrase in q for phrase in _SQL_PHRASES):
        return "sql"
    return "research"


def make_llm_router(generator: Generator, registry: AgentRegistry) -> Router:
    """Build a router that asks the LLM to pick one of the registered agents."""
    options = registry.describe()
    names = set(registry.names())
    fallback = registry.names()[0]

    def _route(query: str) -> str:
        system = (
            "You route a user question to exactly one agent. Reply with ONLY the "
            "agent's name and nothing else.\n\nAgents:\n" + options
        )
        raw = generator.generate(system, query).strip().lower()
        choice = raw.split()[0] if raw else ""
        return choice if choice in names else fallback

    return _route


class OrchestratorState(TypedDict):
    query: str
    context: AgentContext | None
    route: str
    run: AgentRun | None


class Orchestrator:
    """Routes between registered agents using a compiled LangGraph graph."""

    def __init__(
        self,
        registry: AgentRegistry,
        *,
        router: Router | None = None,
        default_agent: str | None = None,
    ) -> None:
        if len(registry) == 0:
            raise ValueError("orchestrator needs at least one registered agent")
        self._registry = registry
        self._router = router or keyword_router
        self._default = default_agent or registry.names()[0]
        if self._default not in registry:
            raise ValueError(f"default agent {self._default!r} is not registered")
        self._graph = self._build()

    def _validated_route(self, query: str) -> str:
        choice = self._router(query)
        return choice if choice in self._registry else self._default

    def _route_node(self, state: OrchestratorState) -> dict[str, Any]:
        return {"route": self._validated_route(state["query"])}

    def _make_agent_node(
        self, name: str
    ) -> Callable[[OrchestratorState], dict[str, Any]]:
        agent = self._registry.get(name)

        def _node(state: OrchestratorState) -> dict[str, Any]:
            return {"run": agent.run(state["query"], state.get("context"))}

        return _node

    def _build(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node("classify", self._route_node)
        for name in self._registry.names():
            builder.add_node(name, self._make_agent_node(name))
            builder.add_edge(name, END)
        builder.add_edge(START, "classify")
        builder.add_conditional_edges(
            "classify",
            lambda state: state["route"],
            {name: name for name in self._registry.names()},
        )
        return builder.compile()

    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        final = self._graph.invoke(
            {"query": query, "context": context, "route": "", "run": None}
        )
        return final["run"]

    @property
    def graph(self):
        """The compiled LangGraph graph (useful for inspection/visualisation)."""
        return self._graph
