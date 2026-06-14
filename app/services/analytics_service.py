"""Analytics: record usage events and aggregate them into a dashboard summary.

All reads are scoped to an organization + workspace. Most figures are derived
from data we already persist (conversations, messages, documents, agent runs);
chat latency and the query-type mix come from the lightweight analytics event
log, so they populate as the workspace is used.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRunRecord
from app.models.analytics import AnalyticsEvent
from app.models.conversation import Conversation, Message, MessageRole
from app.models.document import Document, DocumentStatus


async def record_event(
    db: AsyncSession,
    *,
    organization_id: str,
    workspace_id: str | None,
    event_type: str,
    name: str | None = None,
    latency_ms: int | None = None,
) -> AnalyticsEvent:
    """Append one usage event. The caller's transaction commits it."""
    event = AnalyticsEvent(
        organization_id=organization_id,
        workspace_id=workspace_id,
        event_type=event_type,
        name=name,
        latency_ms=latency_ms,
    )
    db.add(event)
    await db.flush()
    return event


async def _scalar(db: AsyncSession, stmt) -> int:
    return int((await db.execute(stmt)).scalar() or 0)


async def build_summary(
    db: AsyncSession, organization_id: str, workspace_id: str
) -> dict:
    """Aggregate every dashboard metric for one workspace."""
    org_ws = (
        Conversation.organization_id == organization_id,
        Conversation.workspace_id == workspace_id,
    )

    # --- conversations & messages (existing tables) ---
    conversations = await _scalar(
        db, select(func.count(Conversation.id)).where(*org_ws)
    )

    msg_join = select(Message).join(
        Conversation, Message.conversation_id == Conversation.id
    )
    messages_total = await _scalar(
        db,
        select(func.count(Message.id))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(*org_ws),
    )
    messages_user = await _scalar(
        db,
        msg_join.with_only_columns(func.count(Message.id)).where(
            *org_ws, Message.role == MessageRole.USER
        ),
    )
    messages_assistant = messages_total - messages_user

    feedback_up = await _scalar(
        db,
        msg_join.with_only_columns(func.count(Message.id)).where(
            *org_ws, Message.feedback == "up"
        ),
    )
    feedback_down = await _scalar(
        db,
        msg_join.with_only_columns(func.count(Message.id)).where(
            *org_ws, Message.feedback == "down"
        ),
    )

    # --- documents ---
    doc_ws = (
        Document.organization_id == organization_id,
        Document.workspace_id == workspace_id,
    )
    documents = await _scalar(db, select(func.count(Document.id)).where(*doc_ws))
    documents_ready = await _scalar(
        db,
        select(func.count(Document.id)).where(
            *doc_ws, Document.status == DocumentStatus.READY
        ),
    )
    chunks_total = await _scalar(
        db, select(func.coalesce(func.sum(Document.num_chunks), 0)).where(*doc_ws)
    )

    # --- agent runs (existing table) -> agent mix ---
    run_ws = (
        AgentRunRecord.organization_id == organization_id,
        AgentRunRecord.workspace_id == workspace_id,
    )
    agent_runs = await _scalar(db, select(func.count(AgentRunRecord.id)).where(*run_ws))
    agent_rows = (
        await db.execute(
            select(AgentRunRecord.agent, func.count(AgentRunRecord.id))
            .where(*run_ws)
            .group_by(AgentRunRecord.agent)
        )
    ).all()
    agent_mix = [{"label": a or "unknown", "count": int(n)} for a, n in agent_rows]

    # --- analytics events (latency + query-type mix + chat time series) ---
    ev_chat = (
        AnalyticsEvent.organization_id == organization_id,
        AnalyticsEvent.workspace_id == workspace_id,
        AnalyticsEvent.event_type == "chat",
    )
    avg_latency = (
        await db.execute(
            select(func.avg(AnalyticsEvent.latency_ms)).where(
                *ev_chat, AnalyticsEvent.latency_ms.isnot(None)
            )
        )
    ).scalar()
    avg_latency_ms = int(avg_latency) if avg_latency is not None else None

    qtype_rows = (
        await db.execute(
            select(AnalyticsEvent.name, func.count(AnalyticsEvent.id))
            .where(*ev_chat, AnalyticsEvent.name.isnot(None))
            .group_by(AnalyticsEvent.name)
        )
    ).all()
    query_type_mix = sorted(
        ({"label": name, "count": int(n)} for name, n in qtype_rows),
        key=lambda r: r["count"],
        reverse=True,
    )

    # Activity over time from user messages (always populated once chatting).
    day = func.date(Message.created_at)
    activity_rows = (
        await db.execute(
            msg_join.with_only_columns(day, func.count(Message.id))
            .where(*org_ws, Message.role == MessageRole.USER)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    activity = [{"date": str(d), "count": int(n)} for d, n in activity_rows]

    total_queries = messages_user + agent_runs

    return {
        "total_queries": total_queries,
        "avg_latency_ms": avg_latency_ms,
        "conversations": conversations,
        "messages_total": messages_total,
        "messages_user": messages_user,
        "messages_assistant": messages_assistant,
        "feedback_up": feedback_up,
        "feedback_down": feedback_down,
        "documents": documents,
        "documents_ready": documents_ready,
        "chunks_total": chunks_total,
        "agent_runs": agent_runs,
        "by_type": [
            {"label": "chat", "count": messages_user},
            {"label": "agent", "count": agent_runs},
        ],
        "agent_mix": agent_mix,
        "query_type_mix": query_type_mix,
        "activity": activity,
    }
