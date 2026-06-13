"""Persistence for agent run traces, scoped to the caller's organization."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentRun
from app.models.agent_run import AgentRunRecord


def _json_safe(obj):
    """Coerce arbitrary run metadata into something the JSON column accepts."""
    return json.loads(json.dumps(obj, default=str))


def serialize_steps(run: AgentRun) -> list[dict]:
    return [
        {
            "thought": s.thought,
            "tool": s.tool,
            "tool_input": s.tool_input,
            "observation": s.observation,
        }
        for s in run.steps
    ]


def serialize_citations(run: AgentRun) -> list[dict]:
    return [
        {
            "index": c.index,
            "source": c.source,
            "page_number": c.page_number,
            "snippet": c.text[:200],
        }
        for c in run.citations
    ]


async def create_run(
    db: AsyncSession,
    *,
    organization_id: str,
    workspace_id: str,
    conversation_id: str | None,
    agent: str,
    run: AgentRun,
) -> AgentRunRecord:
    record = AgentRunRecord(
        organization_id=organization_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        agent=agent,
        query=run.query,
        answer=run.answer,
        steps=serialize_steps(run),
        citations=serialize_citations(run),
        run_metadata=_json_safe(run.metadata),
    )
    db.add(record)
    await db.flush()
    return record


async def get_run(db: AsyncSession, run_id: str, org_id: str) -> AgentRunRecord | None:
    result = await db.execute(
        select(AgentRunRecord).where(
            AgentRunRecord.id == run_id,
            AgentRunRecord.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def list_runs(
    db: AsyncSession, *, organization_id: str, workspace_id: str
) -> list[AgentRunRecord]:
    result = await db.execute(
        select(AgentRunRecord)
        .where(
            AgentRunRecord.organization_id == organization_id,
            AgentRunRecord.workspace_id == workspace_id,
        )
        .order_by(AgentRunRecord.created_at.desc())
    )
    return list(result.scalars().all())
