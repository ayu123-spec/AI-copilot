"""Orchestrates ingestion: parse -> clean -> chunk -> embed -> store in Qdrant,
while persisting a Document row for tracking. Everything is tenant-scoped.

Images are routed through the multimodal pipeline: an ImageDescriber turns them
into text, which is then chunked and embedded like any other content and tagged
with ``modality="image"`` so it stays distinguishable at retrieval time.
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chunking.chunkers import chunk_document
from app.core.config import settings
from app.core.logging import get_logger
from app.embeddings.base import Embedder
from app.ingestion.base import ParsedDocument, ParsedPage
from app.ingestion.parsers import IMAGE_CONTENT_TYPE, is_image, parse_file
from app.models.document import Document, DocumentStatus
from app.multimodal.base import ImageDescriber
from app.preprocessing.cleaner import clean_document
from app.vectorstore.qdrant_store import SearchResult, VectorStore

logger = get_logger(__name__)


async def ingest_file(
    db: AsyncSession,
    *,
    path: str,
    filename: str,
    organization_id: str,
    workspace_id: str,
    embedder: Embedder,
    store: VectorStore,
    image_describer: ImageDescriber | None = None,
    strategy: str | None = None,
) -> Document:
    """Run the pipeline for one file and return the created Document record."""
    strategy = strategy or settings.CHUNK_STRATEGY

    ext = Path(path).suffix.lower()
    if is_image(ext):
        if image_describer is None:
            from app.multimodal.factory import get_image_describer

            image_describer = get_image_describer()
        content_type = IMAGE_CONTENT_TYPE.get(ext, "image/png")
        description = image_describer.describe(
            Path(path).read_bytes(), filename=filename, content_type=content_type
        )
        parsed = ParsedDocument(
            filename,
            content_type,
            [ParsedPage(page_number=1, text=description.text)],
            {"source": filename, "modality": "image"},
        )
        modality = "image"
    else:
        parsed = parse_file(path)
        modality = "text"

    parsed = clean_document(parsed)
    parsed.filename = filename  # use the user's original name, not the temp path
    document = Document(
        organization_id=organization_id,
        workspace_id=workspace_id,
        filename=parsed.filename,
        content_type=parsed.content_type,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    await db.flush()  # need document.id for chunk payloads

    try:
        chunks = chunk_document(parsed, strategy=strategy, embedder=embedder)
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "document_id": document.id,
                    "workspace_id": workspace_id,
                    "organization_id": organization_id,
                    "modality": modality,
                }
            )
        vectors = embedder.embed([c.text for c in chunks]) if chunks else []
        store.ensure_collection(embedder.dimension)
        store.upsert_chunks(chunks, vectors)

        document.num_chunks = len(chunks)
        document.status = DocumentStatus.READY
    except Exception as exc:  # noqa: BLE001 - record failure, surface to caller
        document.status = DocumentStatus.FAILED
        document.error = str(exc)[:1024]
        logger.exception("Ingestion failed for %s", parsed.filename)

    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(
    db: AsyncSession, organization_id: str, workspace_id: str
) -> list[Document]:
    result = await db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.workspace_id == workspace_id,
        )
    )
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession, document_id: str, organization_id: str
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


def search_chunks(
    *,
    query: str,
    organization_id: str,
    workspace_id: str,
    embedder: Embedder,
    store: VectorStore,
    limit: int = 5,
) -> list[SearchResult]:
    """Vector search, always filtered to the caller's org + workspace."""
    vector = embedder.embed_query(query)
    return store.search(
        vector,
        limit=limit,
        where={"organization_id": organization_id, "workspace_id": workspace_id},
    )
