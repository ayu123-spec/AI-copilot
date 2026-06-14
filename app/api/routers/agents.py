"""Agentic API: run the orchestrator (or a chosen agent), inspect run traces,
and manage long-term memory. Everything is scoped to the caller's organization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentRun
from app.agents.factory import build_registry
from app.agents.orchestrator import Orchestrator
from app.api.deps import (
    get_analytics_engine,
    get_current_user,
    get_embedder,
    get_generator,
    get_graph_store,
    get_guardrails,
    get_memory_store,
    get_reranker,
    get_vector_store,
)
from app.core.config import settings
from app.db.base import get_db
from app.embeddings.base import Embedder
from app.guardrails.base import INJECTION_REFUSAL
from app.guardrails.guard import Guardrails
from app.memory import build_agent_context, list_memories, recall, remember
from app.models.conversation import MessageRole
from app.models.user import User
from app.rag.llm import Generator
from app.rag.rerank import Reranker
from app.schemas.agents import (
    AgentRunRecordOut,
    AgentRunRequest,
    AgentRunResponse,
    AgentStepOut,
    CitationOut,
    MemoryCreate,
    MemoryOut,
    MemoryRecallRequest,
    RecalledMemoryOut,
)
from app.services import agent_service, chat_service, workspace_service
from app.vectorstore.qdrant_store import VectorStore

router = APIRouter(tags=["agents"])


async def _require_workspace(db, workspace_id, user):
    ws = await workspace_service.get_workspace(db, workspace_id, user.organization_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    return ws


def _steps_out(run: AgentRun) -> list[AgentStepOut]:
    return [
        AgentStepOut(
            thought=s.thought,
            tool=s.tool,
            tool_input=s.tool_input,
            observation=s.observation,
        )
        for s in run.steps
    ]


@router.post("/workspaces/{workspace_id}/agents/run", response_model=AgentRunResponse)
async def run_agent(
    workspace_id: str,
    data: AgentRunRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
    memory_store: VectorStore = Depends(get_memory_store),
    reranker: Reranker = Depends(get_reranker),
    generator: Generator = Depends(get_generator),
    analytics_engine: Engine = Depends(get_analytics_engine),
    graph_store=Depends(get_graph_store),
    guardrails: Guardrails = Depends(get_guardrails),
):
    await _require_workspace(db, workspace_id, current)

    # Input guardrail: refuse prompt-injection / jailbreak attempts before routing.
    gate = guardrails.guard_input(data.query)
    if not gate.allowed:
        import uuid

        return AgentRunResponse(
            run_id=uuid.uuid4().hex,
            conversation_id=data.conversation_id,
            agent="guardrail",
            answer=INJECTION_REFUSAL,
            citations=[],
            steps=[],
            metadata={"blocked": True, "reasons": gate.reasons},
        )

    # Resolve or create the conversation, if we're persisting to history.
    conversation_id = data.conversation_id
    if data.persist_history:
        if conversation_id:
            conv = await chat_service.get_conversation(
                db, conversation_id, current.organization_id
            )
            if conv is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
        else:
            conv = await chat_service.create_conversation(
                db, current.organization_id, workspace_id, title=data.query
            )
        conversation_id = conv.id

    # Short-term (history) + long-term (recalled) memory for this run.
    context = await build_agent_context(
        db,
        memory_store,
        embedder,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        query=data.query,
        conversation_id=conversation_id,
        recall_limit=settings.MEMORY_RECALL_LIMIT,
        history_limit=settings.MEMORY_HISTORY_LIMIT,
    )

    registry = build_registry(
        embedder=embedder,
        store=store,
        reranker=reranker,
        generator=generator,
        analytics_engine=analytics_engine,
        graph_store=graph_store,
        max_rows=settings.SQL_AGENT_MAX_ROWS,
        max_hops=settings.GRAPH_MAX_HOPS,
    )

    if data.agent:
        if data.agent not in registry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown agent: {data.agent}",
            )
        run: AgentRun = registry.get(data.agent).run(data.query, context)
        chosen = data.agent
    else:
        run = Orchestrator(registry, default_agent="research").run(data.query, context)
        chosen = run.metadata.get("agent", "research")

    citations_payload = agent_service.serialize_citations(run)
    if data.persist_history:
        await chat_service.add_message(
            db, conversation_id, MessageRole.USER, data.query
        )
        await chat_service.add_message(
            db, conversation_id, MessageRole.ASSISTANT, run.answer, citations_payload
        )

    record = await agent_service.create_run(
        db,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        agent=chosen,
        run=run,
    )
    await db.commit()

    return AgentRunResponse(
        run_id=record.id,
        conversation_id=conversation_id,
        agent=chosen,
        answer=run.answer,
        citations=[CitationOut(**c) for c in citations_payload],
        steps=_steps_out(run),
        metadata=run.metadata,
    )


@router.get(
    "/workspaces/{workspace_id}/agents/runs",
    response_model=list[AgentRunRecordOut],
)
async def list_agent_runs(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace(db, workspace_id, current)
    return await agent_service.list_runs(
        db, organization_id=current.organization_id, workspace_id=workspace_id
    )


@router.get("/agents/runs/{run_id}", response_model=AgentRunRecordOut)
async def get_agent_run(
    run_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await agent_service.get_run(db, run_id, current.organization_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return record


@router.post(
    "/workspaces/{workspace_id}/memories",
    response_model=MemoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_memory(
    workspace_id: str,
    data: MemoryCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    memory_store: VectorStore = Depends(get_memory_store),
):
    await _require_workspace(db, workspace_id, current)
    return await remember(
        db,
        memory_store,
        embedder,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        content=data.content,
        kind=data.kind,
        source=data.source,
    )


@router.get("/workspaces/{workspace_id}/memories", response_model=list[MemoryOut])
async def get_memories(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace(db, workspace_id, current)
    return await list_memories(
        db, organization_id=current.organization_id, workspace_id=workspace_id
    )


@router.post(
    "/workspaces/{workspace_id}/memories/recall",
    response_model=list[RecalledMemoryOut],
)
async def recall_memories(
    workspace_id: str,
    data: MemoryRecallRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    memory_store: VectorStore = Depends(get_memory_store),
):
    await _require_workspace(db, workspace_id, current)
    hits = recall(
        memory_store,
        embedder,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        query=data.query,
        limit=data.limit or settings.MEMORY_RECALL_LIMIT,
    )
    return [
        RecalledMemoryOut(
            memory_id=h.memory_id, content=h.content, kind=h.kind, score=h.score
        )
        for h in hits
    ]
