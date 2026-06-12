"""Tests for the agent foundation (Phase 3, Part 1)."""

import pytest

from app.agents import (
    Agent,
    AgentContext,
    AgentRegistry,
    AgentRun,
    AgentStep,
    FakeAgent,
    FunctionTool,
    Tool,
    ToolError,
    ToolRegistry,
    ToolResult,
)
from app.rag.engine import Citation


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
def test_tool_result_defaults():
    r = ToolResult(output="hi")
    assert r.output == "hi"
    assert r.metadata == {}


def test_tool_is_abstract():
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_custom_tool_subclass_runs():
    class UpperTool(Tool):
        name = "upper"
        description = "Uppercase the text argument."

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output=str(kwargs.get("text", "")).upper())

    assert UpperTool().run(text="abc").output == "ABC"


def test_function_tool_wraps_string():
    tool = FunctionTool("echo", "Echo back the text.", lambda text: f"got {text}")
    result = tool.run(text="x")
    assert isinstance(result, ToolResult)
    assert result.output == "got x"


def test_function_tool_passes_through_tool_result():
    payload = ToolResult(output="done", metadata={"rows": 3})
    tool = FunctionTool("noop", "Return a prepared result.", lambda: payload)
    assert tool.run() is payload


def test_function_tool_normalises_exceptions():
    def boom(**_):
        raise ValueError("kaboom")

    tool = FunctionTool("boom", "Always fails.", boom)
    with pytest.raises(ToolError) as exc:
        tool.run()
    assert "kaboom" in str(exc.value)


def test_function_tool_propagates_tool_error():
    def boom(**_):
        raise ToolError("explicit")

    tool = FunctionTool("boom", "Raises a ToolError.", boom)
    with pytest.raises(ToolError, match="explicit"):
        tool.run()


# --------------------------------------------------------------------------- #
# ToolRegistry
# --------------------------------------------------------------------------- #
def _echo_tool(name: str = "echo") -> FunctionTool:
    return FunctionTool(name, f"{name} tool", lambda **kw: ToolResult(output="ok"))


def test_tool_registry_register_and_lookup():
    reg = ToolRegistry()
    tool = reg.register(_echo_tool("a"))
    assert "a" in reg
    assert len(reg) == 1
    assert reg.get("a") is tool
    assert reg.names() == ["a"]
    assert reg.tools() == [tool]


def test_tool_registry_describe():
    reg = ToolRegistry()
    reg.register(FunctionTool("a", "does a", lambda: ToolResult(output="")))
    reg.register(FunctionTool("b", "does b", lambda: ToolResult(output="")))
    assert reg.describe() == "a: does a\nb: does b"


def test_tool_registry_rejects_empty_name():
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="non-empty name"):
        reg.register(FunctionTool("", "desc", lambda: ToolResult(output="")))


def test_tool_registry_rejects_empty_description():
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="non-empty description"):
        reg.register(FunctionTool("a", "", lambda: ToolResult(output="")))


def test_tool_registry_rejects_duplicate():
    reg = ToolRegistry()
    reg.register(_echo_tool("dup"))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_echo_tool("dup"))


def test_tool_registry_missing_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="no tool registered"):
        reg.get("nope")


# --------------------------------------------------------------------------- #
# Agent contracts + FakeAgent
# --------------------------------------------------------------------------- #
def test_agent_context_defaults():
    ctx = AgentContext()
    assert ctx.organization_id is None
    assert ctx.workspace_id is None
    assert ctx.history == []
    assert ctx.memories == []
    assert ctx.extra == {}


def test_agent_run_holds_steps_and_citations():
    step = AgentStep(thought="think", tool="t", tool_input={"q": "x"}, observation="o")
    cite = Citation(index=1, source="doc.txt", page_number=2, text="snippet")
    run = AgentRun(query="q", answer="a", steps=[step], citations=[cite])
    assert run.steps[0].observation == "o"
    assert run.citations[0].source == "doc.txt"


def test_agent_is_abstract():
    with pytest.raises(TypeError):
        Agent()  # type: ignore[abstract]


def test_fake_agent_echoes_without_tool():
    run = FakeAgent().run("hello")
    assert run.answer == "Echo: hello"
    assert run.steps == []


def test_fake_agent_uses_tool_output():
    tool = FunctionTool("rev", "reverse", lambda query: query[::-1])
    run = FakeAgent(tool=tool).run("abc")
    assert run.answer == "cba"
    assert len(run.steps) == 1
    step = run.steps[0]
    assert step.tool == "rev"
    assert step.tool_input == {"query": "abc"}
    assert step.observation == "cba"


# --------------------------------------------------------------------------- #
# AgentRegistry
# --------------------------------------------------------------------------- #
def test_agent_registry_register_and_lookup():
    reg = AgentRegistry()
    agent = reg.register(FakeAgent())
    assert "fake" in reg
    assert len(reg) == 1
    assert reg.get("fake") is agent
    assert reg.names() == ["fake"]
    assert reg.describe().startswith("fake: ")


def test_agent_registry_rejects_duplicate():
    reg = AgentRegistry()
    reg.register(FakeAgent())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(FakeAgent())


def test_agent_registry_missing_raises_keyerror():
    reg = AgentRegistry()
    with pytest.raises(KeyError, match="no agent registered"):
        reg.get("nope")
