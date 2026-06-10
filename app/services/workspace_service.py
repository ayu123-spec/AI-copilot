"""Business logic for workspaces, scoped to the caller's organization."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole


async def create_workspace(db: AsyncSession, owner: User, name: str) -> Workspace:
    workspace = Workspace(organization_id=owner.organization_id, name=name)
    db.add(workspace)
    await db.flush()
    db.add(
        WorkspaceMembership(
            workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER
        )
    )
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def list_workspaces(db: AsyncSession, org_id: str) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.organization_id == org_id)
    )
    return list(result.scalars().all())


async def get_workspace(
    db: AsyncSession, workspace_id: str, org_id: str
) -> Workspace | None:
    """Fetch a workspace only if it belongs to the caller's organization."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id, Workspace.organization_id == org_id
        )
    )
    return result.scalar_one_or_none()


async def add_member(
    db: AsyncSession, workspace: Workspace, user: User, role: WorkspaceRole
) -> WorkspaceMembership:
    existing = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    membership = existing.scalar_one_or_none()
    if membership:
        membership.role = role
    else:
        membership = WorkspaceMembership(
            workspace_id=workspace.id, user_id=user.id, role=role
        )
        db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def update_settings(
    db: AsyncSession, workspace: Workspace, updates: dict
) -> Workspace:
    merged = dict(workspace.settings or {})
    merged.update({k: v for k, v in updates.items() if v is not None})
    workspace.settings = merged
    await db.commit()
    await db.refresh(workspace)
    return workspace
