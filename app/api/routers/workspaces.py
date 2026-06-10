"""Workspace endpoints, scoped to the caller's organization."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.base import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    InviteRequest,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceSettingsUpdate,
)
from app.services import auth_service, workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    return await workspace_service.create_workspace(db, current, data.name)


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await workspace_service.list_workspaces(db, current.organization_id)


@router.post("/{workspace_id}/invite", status_code=status.HTTP_200_OK)
async def invite_user(
    workspace_id: str,
    data: InviteRequest,
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    workspace = await workspace_service.get_workspace(
        db, workspace_id, current.organization_id
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    invitee = await auth_service.get_user_by_email(db, data.email)
    # Enforce tenancy: can only invite users already in the same organization.
    if invitee is None or invitee.organization_id != current.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization",
        )

    membership = await workspace_service.add_member(db, workspace, invitee, data.role)
    return {"workspace_id": workspace.id, "user_id": invitee.id, "role": membership.role}


@router.patch("/{workspace_id}/settings", response_model=WorkspaceOut)
async def update_workspace_settings(
    workspace_id: str,
    data: WorkspaceSettingsUpdate,
    current: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    workspace = await workspace_service.get_workspace(
        db, workspace_id, current.organization_id
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await workspace_service.update_settings(
        db, workspace, data.model_dump(exclude_none=True)
    )
