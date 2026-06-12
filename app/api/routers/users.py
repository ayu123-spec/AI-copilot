"""User endpoints, scoped to the caller's organization."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.base import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def read_me(current: User = Depends(get_current_user)):
    return current


@router.get("", response_model=list[UserOut])
async def list_org_users(
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    # Tenant isolation: only ever return users in the caller's organization.
    result = await db.execute(
        select(User).where(User.organization_id == current.organization_id)
    )
    return list(result.scalars().all())
