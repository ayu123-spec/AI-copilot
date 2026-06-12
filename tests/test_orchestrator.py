"""Tests for the LangGraph orchestrator (Phase 3, Part 4)."""

import pytest

from app.agents.base import Agent, AgentContext, AgentRun
from app.agents.orchestrator import Orchestrator, keyword_router, make_llm_router
from app.agents.registry import AgentRegistry
from app.rag.llm import Generator


class _NamedAgent(Agent):
    """A minimal agent that echoes a label and the context's workspace id."""

    def __init__(self, name, reply):
        self.name = name
        self.description = f"{name} agent"
        self._reply = reply

    def run(self, query, context=None):
        ws = context.workspace_id if context else None
        return AgentRun(query=query, answer=f"{self._reply}|ws={ws}")


def _registry():
    reg = AgentRegistry()
    reg.register(_NamedAgent("research", "RESEARCH"))
    reg.register(_NamedAgent("sql", "SQL"))
    return reg


# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #
def test_keyword_router_picks_sql_for_quantitative():
    assert keyword_router("What was total revenue per region?") == "sql"
    assert keyword_router("How many units sold last quarter?") == "sql"


def test_keyword_router_defaults_to_research():
    assert keyword_router("Summarise our security policy") == "research"


class _RouterStub(Generator):
    def __init__(self, reply):
        self._reply = reply

    def generate(self, system, user):
        return self._reply


def test_llm_router_uses_model_choice():
    router = make_llm_router(_RouterStub("sql"), _registry())
    assert router("anything") == "sql"


def test_llm_router_falls_back_on_garbage():
    router = make_llm_router(_RouterStub("i-have-no-idea"), _registry())
    assert router("anything") == "research"  # first registered agent


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
def test_orchestrator_routes_to_sql():
    run = Orchestrator(_registry()).run("What is total revenue by region?")
    assert run.answer.startswith("SQL")


def test_orchestrator_routes_to_research():
    run = Orchestrator(_registry()).run("Explain our data retention policy")
    assert run.answer.startswith("RESEARCH")


def test_orchestrator_passes_context_through():
    run = Orchestrator(_registry()).run(
        "Explain the policy", AgentContext(workspace_id="ws1")
    )
    assert "ws=ws1" in run.answer


def test_orchestrator_unknown_route_falls_back_to_default():
    orch = Orchestrator(
        _registry(), router=lambda q: "does-not-exist", default_agent="research"
    )
    assert orch.run("anything").answer.startswith("RESEARCH")


def test_orchestrator_requires_an_agent():
    with pytest.raises(ValueError, match="at least one"):
        Orchestrator(AgentRegistry())


def test_orchestrator_graph_is_compiled():
    assert Orchestrator(_registry()).graph is not None
