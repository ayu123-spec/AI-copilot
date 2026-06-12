"""Tests for the research agent (Phase 3, Part 2)."""

from app.agents import AgentContext
from app.agents.research import RagSearchTool, ResearchAgent
from app.rag.engine import RagEngine
from app.rag.hybrid import RetrievedChunk
from app.rag.llm import FakeGenerator, Generator
from app.rag.rerank import FakeReranker


def _chunk(i, text="some evidence text", source="doc.txt", page=1):
    return RetrievedChunk(
        id=str(i),
        score=1.0,
        text=text,
        metadata={"source": source, "page_number": page},
    )


class _StubRetriever:
    """Returns fixed chunks for any query and records the last `where` filter."""

    def __init__(self, chunks):
        self._chunks = chunks
        self.last_where: object = "unset"

    def retrieve(self, query, *, where=None, limit=20):
        self.last_where = where
        return self._chunks


def _engine(chunks, generator=None):
    return RagEngine(
        _StubRetriever(chunks), FakeReranker(), generator or FakeGenerator()
    )


def test_rag_search_tool_returns_evidence():
    engine = _engine([_chunk(1, "Paris is the capital.")])
    result = RagSearchTool(engine).run(query="capital?")
    assert "Paris is the capital." in result.output
    assert len(result.metadata["chunks"]) == 1


def test_research_agent_answers_with_citations():
    engine = _engine([_chunk(1, "Paris is the capital.", source="geo.txt")])
    run = ResearchAgent(engine).run("What is the capital?")
    assert run.answer
    assert run.citations and run.citations[0].source == "geo.txt"
    assert any(s.tool == "rag_search" for s in run.steps)


def test_research_agent_no_evidence_path():
    run = ResearchAgent(_engine([])).run("anything")
    assert run.citations == []
    assert "enough information" in run.answer.lower()


def test_research_agent_is_tenant_scoped():
    retriever = _StubRetriever([_chunk(1)])
    engine = RagEngine(retriever, FakeReranker(), FakeGenerator())
    ResearchAgent(engine).run("q", AgentContext(workspace_id="ws1"))
    assert retriever.last_where == {"workspace_id": "ws1"}


class _Planner(Generator):
    """First call returns follow-up lines; later calls return a normal answer."""

    def __init__(self, followups_text):
        self._fu = followups_text
        self.calls = 0

    def generate(self, system, user):
        self.calls += 1
        return self._fu if self.calls == 1 else "Synthesised answer [1]."


def test_research_agent_multi_hop_dedupes_evidence():
    shared = _chunk(1, "shared evidence")
    retriever = _StubRetriever([shared])  # same chunk for every query
    engine = RagEngine(retriever, FakeReranker(), _Planner("a follow-up question"))
    run = ResearchAgent(engine, max_followups=2).run("original question")

    retrieval_steps = [s for s in run.steps if s.tool == "rag_search"]
    assert len(retrieval_steps) == 2  # original + one follow-up
    assert len(run.citations) == 1  # de-duplicated to a single chunk
