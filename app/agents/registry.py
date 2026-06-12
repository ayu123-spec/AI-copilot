"""Registries mapping names to tools and agents.

An orchestrator (added in a later part) looks objects up by name, and an LLM can
be shown :meth:`describe` to decide what to call. Registration validates that
names and descriptions are present and unique so misconfiguration fails loudly.
"""

from app.agents.base import Agent
from app.agents.tools import Tool


class ToolRegistry:
    """An ordered, name-keyed collection of :class:`Tool` instances."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if not tool.name:
            raise ValueError("tool must have a non-empty name")
        if not tool.description:
            raise ValueError(f"tool {tool.name!r} must have a non-empty description")
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"no tool registered under {name!r}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def names(self) -> list[str]:
        return list(self._tools)

    def tools(self) -> list[Tool]:
        return list(self._tools.values())

    def describe(self) -> str:
        """A newline-separated ``name: description`` list, for prompting an LLM."""
        return "\n".join(f"{t.name}: {t.description}" for t in self._tools.values())


class AgentRegistry:
    """An ordered, name-keyed collection of :class:`Agent` instances."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        if not agent.name:
            raise ValueError("agent must have a non-empty name")
        if not agent.description:
            raise ValueError(f"agent {agent.name!r} must have a non-empty description")
        if agent.name in self._agents:
            raise ValueError(f"agent {agent.name!r} is already registered")
        self._agents[agent.name] = agent
        return agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError:
            raise KeyError(f"no agent registered under {name!r}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._agents

    def __len__(self) -> int:
        return len(self._agents)

    def names(self) -> list[str]:
        return list(self._agents)

    def agents(self) -> list[Agent]:
        return list(self._agents.values())

    def describe(self) -> str:
        """A newline-separated ``name: description`` list, for routing/prompting."""
        return "\n".join(f"{a.name}: {a.description}" for a in self._agents.values())
