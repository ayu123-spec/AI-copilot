"""Document ingestion + search endpoints, scoped to org + workspace."""
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_embedder, get_vector_store, require_roles
from app.db.base import get_db
from app.embeddings.base import Embedder
from app.ingestion.parsers import EXTENSION_CONTENT_TYPE, UnsupportedFileType
from app.models.user import User, UserRole
from app.schemas.document import DocumentOut, SearchRequest, SearchResultOut
from app.services import ingestion_service, workspace_service
from app.vectorstore.qdrant_store import VectorStore

router = APIRouter(tags=["documents"])


async def _require_workspace(db, workspace_id: str, user: User):
    ws = await workspace_service.get_workspace(db, workspace_id, user.organization_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    await _require_workspace(db, workspace_id, current)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXTENSION_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {ext or 'unknown'}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        document = await ingestion_service.ingest_file(
            db,
            path=tmp_path,
            filename=file.filename or f"upload{ext}",
            organization_id=current.organization_id,
            workspace_id=workspace_id,
            embedder=embedder,
            store=store,
        )
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    finally:
        os.unlink(tmp_path)
    return document


@router.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace(db, workspace_id, current)
    return await ingestion_service.list_documents(db, current.organization_id, workspace_id)


@router.post("/workspaces/{workspace_id}/search", response_model=list[SearchResultOut])
async def search_documents(
    workspace_id: str,
    data: SearchRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    await _require_workspace(db, workspace_id, current)
    results = ingestion_service.search_chunks(
        query=data.query,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        embedder=embedder,
        store=store,
        limit=data.limit,
    )
    return [
        SearchResultOut(
            score=r.score,
            text=r.text,
            document_id=r.metadata.get("document_id"),
            page_number=r.metadata.get("page_number"),
            source=r.metadata.get("source"),
        )
        for r in results
    ]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
    store: VectorStore = Depends(get_vector_store),
):
    doc = await ingestion_service.get_document(db, document_id, current.organization_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    store.delete_by_document(document_id)
    await db.delete(doc)
    await db.commit()
