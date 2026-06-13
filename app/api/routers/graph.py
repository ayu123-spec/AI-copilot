"""Knowledge-graph API (Phase 4): build a workspace's graph from its documents,
search entities, traverse relationships, and run GraphRAG retrieval. Everything
is scoped to the caller's organization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_entity_extractor,
    get_graph_store,
    get_vector_store,
)
from app.core.config import settings
from app.db.base import get_db
from app.graph import GraphRetriever, build_graph_from_texts
from app.graph.base import GraphStore
from app.graph.extract import EntityExtractor
from app.models.user import User
from app.schemas.graph import (
    EntityOut,
    GraphBuildRequest,
    GraphBuildResponse,
    GraphFactOut,
    GraphQueryRequest,
    GraphQueryResponse,
)
from app.services import workspace_service
from app.vectorstore.qdrant_store import VectorStore

router = APIRouter(tags=["graph"])


async def _require_workspace(db, workspace_id, user):
    ws = await workspace_service.get_workspace(db, workspace_id, user.organization_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    return ws


def _facts_out(facts) -> list[GraphFactOut]:
    return [
        GraphFactOut(source=f.source, relation=f.relation, target=f.target)
        for f in facts
    ]


@router.get("/workspaces/{workspace_id}/graph", response_model=GraphQueryResponse)
async def get_graph(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph_store: GraphStore = Depends(get_graph_store),
):
    """The whole workspace graph (all entities + relationships) for visualisation."""
    await _require_workspace(db, workspace_id, current)
    entities, facts = graph_store.export_graph(
        organization_id=current.organization_id, workspace_id=workspace_id
    )
    return GraphQueryResponse(
        entities=[EntityOut(id=e.id, name=e.name, type=e.type) for e in entities],
        facts=_facts_out(facts),
    )


@router.post(
    "/workspaces/{workspace_id}/graph/build", response_model=GraphBuildResponse
)
async def build_graph(
    workspace_id: str,
    data: GraphBuildRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph_store: GraphStore = Depends(get_graph_store),
    extractor: EntityExtractor = Depends(get_entity_extractor),
    store: VectorStore = Depends(get_vector_store),
):
    await _require_workspace(db, workspace_id, current)

    texts = data.texts
    if not texts:
        # Build from the workspace's already-ingested document chunks.
        chunks = store.fetch_all(
            where={
                "organization_id": current.organization_id,
                "workspace_id": workspace_id,
            }
        )
        texts = [c.text for c in chunks if c.text]

    result = build_graph_from_texts(
        graph_store,
        extractor,
        texts,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
    )
    return GraphBuildResponse(
        entities=result.entities, relationships=result.relationships
    )


@router.get("/workspaces/{workspace_id}/graph/entities", response_model=list[EntityOut])
async def search_entities(
    workspace_id: str,
    q: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph_store: GraphStore = Depends(get_graph_store),
):
    await _require_workspace(db, workspace_id, current)
    ents = graph_store.search_entities(
        q,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        limit=20,
    )
    return [EntityOut(id=e.id, name=e.name, type=e.type) for e in ents]


@router.get(
    "/workspaces/{workspace_id}/graph/entities/{name}/neighbors",
    response_model=GraphQueryResponse,
)
async def entity_neighbors(
    workspace_id: str,
    name: str,
    depth: int = 1,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph_store: GraphStore = Depends(get_graph_store),
):
    await _require_workspace(db, workspace_id, current)
    ent = graph_store.get_entity(
        name, organization_id=current.organization_id, workspace_id=workspace_id
    )
    if ent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found"
        )
    facts = graph_store.neighbors(
        ent.id,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        depth=depth,
    )
    return GraphQueryResponse(
        entities=[EntityOut(id=ent.id, name=ent.name, type=ent.type)],
        facts=_facts_out(facts),
    )


@router.post(
    "/workspaces/{workspace_id}/graph/query", response_model=GraphQueryResponse
)
async def query_graph(
    workspace_id: str,
    data: GraphQueryRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph_store: GraphStore = Depends(get_graph_store),
):
    await _require_workspace(db, workspace_id, current)
    retriever = GraphRetriever(graph_store, max_hops=settings.GRAPH_MAX_HOPS)
    ctx = retriever.retrieve(
        data.query,
        organization_id=current.organization_id,
        workspace_id=workspace_id,
        depth=data.depth,
    )
    return GraphQueryResponse(
        entities=[EntityOut(id=e.id, name=e.name, type=e.type) for e in ctx.entities],
        facts=_facts_out(ctx.facts),
    )
