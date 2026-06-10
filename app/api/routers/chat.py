"""RAG chat endpoint — ask a question, get a grounded answer with citations."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_embedder,
    get_generator,
    get_reranker,
    get_vector_store,
)
from app.db.base import get_db
from app.embeddings.base import Embedder
from app.models.user import User
from app.rag.engine import RagEngine
from app.rag.hybrid import HybridRetriever
from app.rag.llm import Generator
from app.rag.rerank import Reranker
from app.schemas.chat import ChatRequest, ChatResponse, CitationOut
from app.services import workspace_service
from app.vectorstore.qdrant_store import VectorStore

router = APIRouter(tags=["chat"])


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
):
    ws = await workspace_service.get_workspace(db, workspace_id, current.organization_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    engine = RagEngine(HybridRetriever(store, embedder), reranker, generator)
    result = engine.answer(
        data.query,
        where={
            "organization_id": current.organization_id,
            "workspace_id": workspace_id,
        },
    )
    return ChatResponse(
        answer=result.answer,
        citations=[
            CitationOut(
                index=c.index,
                source=c.source,
                page_number=c.page_number,
                snippet=c.text[:200],
            )
            for c in result.citations
        ],
    )
