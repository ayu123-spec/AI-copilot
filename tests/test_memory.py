"""Tests for the agent memory service (Phase 3, Part 5)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.agents.research import ResearchAgent
from app.embeddings.embedders import FakeEmbedder
from app.memory import (
    build_agent_context,
    list_memories,
    recall,
    recent_history,
    remember,
)
from app.models.conversation import Message, MessageRole
from app.models.memory import MemoryKind
from app.rag.engine import RagEngine
from app.rag.llm import FakeGenerator
from app.rag.rerank import FakeReranker
from app.vectorstore.qdrant_store import VectorStore


@pytest.fixture
def embedder():
    return FakeEmbedder(dim=64)


@pytest.fixture
def mem_store():
    return VectorStore(collection="test_mem", location=":memory:")


async def test_remember_persists_and_is_recallable(db_session, mem_store, embedder):
    item = await remember(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        content="The launch is scheduled for March.",
        kind=MemoryKind.FACT,
    )
    assert item.id  # row persisted with an id

    hits = recall(
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        query="When is the launch?",
        limit=5,
    )
    assert any("March" in h.content for h in hits)
    assert hits[0].memory_id == item.id


async def test_recall_is_tenant_scoped(db_session, mem_store, embedder):
    await remember(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        content="Secret only ws1 should see.",
    )
    other = recall(
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws2",
        query="secret",
        limit=5,
    )
    assert other == []


async def test_list_memories_scoped(db_session, mem_store, embedder):
    await remember(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        content="a",
    )
    await remember(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws2",
        content="b",
    )
    items = await list_memories(db_session, organization_id="org1", workspace_id="ws1")
    assert [i.content for i in items] == ["a"]


async def test_recent_history_orders_and_limits(db_session):
    base = datetime.now(UTC)
    for i, (role, text) in enumerate(
        [
            (MessageRole.USER, "first"),
            (MessageRole.ASSISTANT, "second"),
            (MessageRole.USER, "third"),
        ]
    ):
        db_session.add(
            Message(
                conversation_id="c1",
                role=role,
                content=text,
                created_at=base + timedelta(seconds=i),
            )
        )
    await db_session.commit()

    hist = await recent_history(db_session, conversation_id="c1", limit=2)
    assert [h["content"] for h in hist] == ["second", "third"]  # last 2, chronological
    assert hist[0]["role"] == "assistant"


async def test_build_agent_context_combines_memory_and_history(
    db_session, mem_store, embedder
):
    await remember(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        content="Customer prefers email over phone.",
        kind=MemoryKind.PREFERENCE,
    )
    db_session.add(
        Message(conversation_id="c9", role=MessageRole.USER, content="hello there")
    )
    await db_session.commit()

    ctx = await build_agent_context(
        db_session,
        mem_store,
        embedder,
        organization_id="org1",
        workspace_id="ws1",
        query="how should we contact them?",
        conversation_id="c9",
        recall_limit=5,
        history_limit=10,
    )
    assert ctx.workspace_id == "ws1"
    assert any("prefers email" in m for m in ctx.memories)
    assert ctx.history and ctx.history[0]["content"] == "hello there"


def test_research_agent_answers_from_memory_without_documents():
    """With no document evidence but a relevant memory, the agent still answers."""

    class _Empty:
        def retrieve(self, query, *, where=None, limit=20):
            return []

    from app.agents.base import AgentContext

    engine = RagEngine(_Empty(), FakeReranker(), FakeGenerator())
    ctx = AgentContext(memories=["The office WiFi password is on the whiteboard."])
    run = ResearchAgent(engine).run("What's the WiFi password?", ctx)
    assert "enough information" not in run.answer.lower()  # it used memory
