"""Agent memory service.

Two layers, both tenant-scoped:

* **Long-term memory** — durable :class:`MemoryItem` rows whose content is
  embedded into the Qdrant memory collection for semantic recall across
  conversations (:func:`remember` / :func:`recall`).
* **Short-term memory** — the recent turns of the current conversation, read
  straight from the ``messages`` table (:func:`recent_history`).

:func:`build_agent_context` assembles both into an :class:`AgentContext` for an
agent run. All DB/vector work happens here in the async layer; the agent itself
stays synchronous and just consumes the populated context.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.embeddings.base import Embedder
from app.models.conversation import Message
from app.models.memory import MemoryItem, MemoryKind
from app.vectorstore.qdrant_store import VectorStore


@dataclass
class RecalledMemory:
    memory_id: str
    content: str
    kind: str
    score: float


def _scope(organization_id: str, workspace_id: str) -> dict:
    return {"organization_id": organization_id, "workspace_id": workspace_id}


async def remember(
    db: AsyncSession,
    store: VectorStore,
    embedder: Embedder,
    *,
    organization_id: str,
    workspace_id: str,
    content: str,
    kind: MemoryKind = MemoryKind.NOTE,
    source: str | None = None,
) -> MemoryItem:
    """Persist a memory row and index its embedding for semantic recall."""
    item = MemoryItem(
        organization_id=organization_id,
        workspace_id=workspace_id,
        kind=kind,
        content=content,
        source=source,
    )
    db.add(item)
    await db.flush()  # assigns item.id

    store.ensure_collection(embedder.dimension)
    payload = {**_scope(organization_id, workspace_id), "kind": kind.value}
    store.upsert_records([(item.id, content, payload)], [embedder.embed_query(content)])
    await db.commit()
    return item


def recall(
    store: VectorStore,
    embedder: Embedder,
    *,
    organization_id: str,
    workspace_id: str,
    query: str,
    limit: int,
) -> list[RecalledMemory]:
    """Return the most semantically relevant memories for ``query``, scoped to
    the tenant. Pure read — no DB session needed."""
    hits = store.search(
        embedder.embed_query(query),
        limit=limit,
        where=_scope(organization_id, workspace_id),
    )
    return [
        RecalledMemory(
            memory_id=h.id,
            content=h.text,
            kind=h.metadata.get("kind", MemoryKind.NOTE.value),
            score=h.score,
        )
        for h in hits
    ]


async def list_memories(
    db: AsyncSession, *, organization_id: str, workspace_id: str
) -> list[MemoryItem]:
    result = await db.execute(
        select(MemoryItem)
        .where(
            MemoryItem.organization_id == organization_id,
            MemoryItem.workspace_id == workspace_id,
        )
        .order_by(MemoryItem.created_at.desc())
    )
    return list(result.scalars().all())


async def recent_history(
    db: AsyncSession, *, conversation_id: str, limit: int
) -> list[dict[str, str]]:
    """The last ``limit`` messages of a conversation, oldest-first, as
    ``{"role", "content"}`` dicts — the agent's short-term memory."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # back to chronological order
    return [{"role": m.role.value, "content": m.content} for m in messages]


async def build_agent_context(
    db: AsyncSession,
    store: VectorStore,
    embedder: Embedder,
    *,
    organization_id: str,
    workspace_id: str,
    query: str,
    conversation_id: str | None = None,
    recall_limit: int,
    history_limit: int,
) -> AgentContext:
    """Assemble an :class:`AgentContext` with long-term memories (recalled for
    ``query``) and short-term history (recent turns of ``conversation_id``)."""
    memories = recall(
        store,
        embedder,
        organization_id=organization_id,
        workspace_id=workspace_id,
        query=query,
        limit=recall_limit,
    )
    history: list[dict[str, str]] = []
    if conversation_id:
        history = await recent_history(
            db, conversation_id=conversation_id, limit=history_limit
        )
    return AgentContext(
        organization_id=organization_id,
        workspace_id=workspace_id,
        history=history,
        memories=[m.content for m in memories],
    )
