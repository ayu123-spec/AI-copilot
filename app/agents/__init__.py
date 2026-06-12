"""Agent foundation: contracts, registries, and fakes that later parts build on.

The research agent, SQL agent, orchestration graph, and memory all sit on top of
the abstractions exported here.
"""

from app.agents.base import Agent, AgentContext, AgentRun, AgentStep
from app.agents.fake import FakeAgent
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.tools import FunctionTool, Tool, ToolError, ToolResult

__all__ = [
    "Agent",
    "AgentContext",
    "AgentRun",
    "AgentStep",
    "AgentRegistry",
    "ToolRegistry",
    "Tool",
    "ToolError",
    "ToolResult",
    "FunctionTool",
    "FakeAgent",
]
