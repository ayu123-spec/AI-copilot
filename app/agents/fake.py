"""A deterministic, offline agent for tests and wiring.

:class:`FakeAgent` needs no LLM. On its own it echoes the query; given a tool, it
calls that tool once and uses the tool's output as the answer, recording a single
:class:`AgentStep`. This lets the agent/tool/registry contracts be exercised end
to end with no keys or network.
"""

from app.agents.base import Agent, AgentContext, AgentRun, AgentStep
from app.agents.tools import Tool


class FakeAgent(Agent):
    name = "fake"
    description = "Deterministic test agent; optionally calls a single tool."

    def __init__(self, tool: Tool | None = None) -> None:
        self._tool = tool

    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        steps: list[AgentStep] = []
        observation: str | None = None
        if self._tool is not None:
            result = self._tool.run(query=query)
            observation = result.output
            steps.append(
                AgentStep(
                    thought=f"Use {self._tool.name} to handle the query.",
                    tool=self._tool.name,
                    tool_input={"query": query},
                    observation=observation,
                )
            )
        answer = observation if observation is not None else f"Echo: {query}"
        return AgentRun(query=query, answer=answer, steps=steps)
