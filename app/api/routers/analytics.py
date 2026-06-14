"""Analytics dashboard: usage metrics for a workspace, scoped to the caller's org."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary
from app.services import analytics_service, workspace_service

router = APIRouter(tags=["analytics"])


@router.get(
    "/workspaces/{workspace_id}/analytics", response_model=AnalyticsSummary
)
async def workspace_analytics(
    workspace_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await workspace_service.get_workspace(
        db, workspace_id, current.organization_id
    )
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    return await analytics_service.build_summary(
        db, current.organization_id, workspace_id
    )
