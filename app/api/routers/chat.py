"""RAG chat: grounded cited answers, streaming, history, and feedback."""

import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_embedder,
    get_generator,
    get_guardrails,
    get_reranker,
    get_vector_store,
)
from app.db.base import get_db
from app.embeddings.base import Embedder
from app.guardrails.base import INJECTION_REFUSAL
from app.guardrails.guard import Guardrails
from app.models.conversation import MessageRole
from app.models.user import User
from app.rag.engine import RagEngine
from app.rag.hybrid import HybridRetriever
from app.rag.llm import Generator
from app.rag.rerank import Reranker
from app.reasoning.followups import suggest_followups
from app.reasoning.research import DeepResearchEngine
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationOut,
    ConversationOut,
    FeedbackRequest,
    MessageOut,
    ResearchStepOut,
)
from app.services import analytics_service, chat_service, workspace_service
from app.vectorstore.qdrant_store import VectorStore

router = APIRouter(tags=["chat"])


async def _require_workspace(db, workspace_id, user):
    ws = await workspace_service.get_workspace(db, workspace_id, user.organization_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    return ws


def _citation_payload(citations):
    return [
        {
            "index": c.index,
            "source": c.source,
            "page_number": c.page_number,
            "snippet": c.text[:200],
        }
        for c in citations
    ]


@router.post("/workspaces/{workspace_id}/chat", response_model=ChatResponse)
async def chat(
    workspace_id: str,
    data: ChatRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
    reranker: Reranker = Depends(get_reranker),
    generator: Generator = Depends(get_generator),
    guardrails: Guardrails = Depends(get_guardrails),
):
    await _require_workspace(db, workspace_id, current)

    # Resolve or create the conversation this turn belongs to.
    if data.conversation_id:
        conv = await chat_service.get_conversation(
            db, data.conversation_id, current.organization_id
        )
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
    else:
        conv = await chat_service.create_conversation(
            db, current.organization_id, workspace_id, title=data.query
        )

    # Input guardrail: block prompt-injection / jailbreak attempts.
    gate = guardrails.guard_input(data.query)
    if not gate.allowed:
        await chat_service.add_message(db, conv.id, MessageRole.USER, data.query)
        assistant = await chat_service.add_message(
            db, conv.id, MessageRole.ASSISTANT, INJECTION_REFUSAL, []
        )
        await db.commit()
        return ChatResponse(
            conversation_id=conv.id,
            message_id=assistant.id,
            answer=INJECTION_REFUSAL,
            citations=[],
        )

    engine = RagEngine(HybridRetriever(store, embedder), reranker, generator)
    where = {
        "organization_id": current.organization_id,
        "workspace_id": workspace_id,
    }
    # Conversation memory: prior turns inform both retrieval and the answer.
    prior = await chat_service.list_messages(db, conv.id)
    history = [(m.role.value, m.content) for m in prior]

    started = time.perf_counter()
    if data.deep_research:
        research = DeepResearchEngine(engine).research(
            data.query, where=where, history=history
        )
        answer_raw = research.answer
        citation_objs = research.citations
        query_type = research.query_type
        steps = research.steps
        event_type = "research"
    else:
        result = engine.answer(data.query, where=where, history=history)
        answer_raw = result.answer
        citation_objs = result.citations
        query_type = result.query_type
        steps = []
        event_type = "chat"
    latency_ms = int((time.perf_counter() - started) * 1000)

    citations = _citation_payload(citation_objs)
    # Output guardrail: redact any PII/secrets before persisting or returning.
    safe = guardrails.guard_output(
        answer_raw, contexts=[c["snippet"] for c in citations]
    )
    await chat_service.add_message(db, conv.id, MessageRole.USER, data.query)
    assistant = await chat_service.add_message(
        db, conv.id, MessageRole.ASSISTANT, safe.text, citations
    )
    await analytics_service.record_event(
        db,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        event_type=event_type,
        name=query_type,
        latency_ms=latency_ms,
    )
    await db.commit()

    n_cites = len(citations)
    grounding = (
        "grounded" if n_cites >= 2 else "partial" if n_cites == 1 else "ungrounded"
    )
    return ChatResponse(
        conversation_id=conv.id,
        message_id=assistant.id,
        answer=safe.text,
        citations=[CitationOut(**c) for c in citations],
        query_type=query_type,
        follow_ups=suggest_followups(query_type),
        grounding=grounding,
        research_steps=[
            ResearchStepOut(sub_question=s.sub_question, sources_found=s.sources_found)
            for s in steps
        ],
    )


@router.post("/workspaces/{workspace_id}/chat/stream")
async def chat_stream(
    workspace_id: str,
    data: ChatRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
    reranker: Reranker = Depends(get_reranker),
    generator: Generator = Depends(get_generator),
    guardrails: Guardrails = Depends(get_guardrails),
):
    """Server-sent events: streams answer tokens, then a final event with
    citations. (This endpoint streams only; use /chat to persist to history.)"""
    await _require_workspace(db, workspace_id, current)

    # Input guardrail: refuse injected/jailbreak prompts before streaming.
    if not guardrails.guard_input(data.query).allowed:

        def refusal_stream():
            yield f"data: {json.dumps({'token': INJECTION_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': []})}\n\n"

        return StreamingResponse(refusal_stream(), media_type="text/event-stream")

    engine = RagEngine(HybridRetriever(store, embedder), reranker, generator)
    citations, tokens = engine.stream(
        data.query,
        where={
            "organization_id": current.organization_id,
            "workspace_id": workspace_id,
        },
    )

    def event_stream():
        for token in tokens:
            yield f"data: {json.dumps({'token': token})}\n\n"
        done = {"done": True, "citations": _citation_payload(citations)}
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/workspaces/{workspace_id}/conversations", response_model=list[ConversationOut]
)
async def list_conversations(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace(db, workspace_id, current)
    return await chat_service.list_conversations(
        db, current.organization_id, workspace_id
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageOut]
)
async def list_messages(
    conversation_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await chat_service.get_conversation(
        db, conversation_id, current.organization_id
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return await chat_service.list_messages(db, conversation_id)


@router.post("/messages/{message_id}/feedback", response_model=MessageOut)
async def submit_feedback(
    message_id: str,
    data: FeedbackRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = await chat_service.get_message(db, message_id, current.organization_id)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    return await chat_service.set_feedback(db, msg, data.rating)
