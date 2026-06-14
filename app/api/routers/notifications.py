"""Notifications feed endpoints, scoped to the caller's organization."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.notification import NotificationOut, UnreadCount
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    workspace_id: str | None = None,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.list_notifications(
        db, current.organization_id, workspace_id
    )


@router.get("/notifications/unread_count", response_model=UnreadCount)
async def unread_count(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return UnreadCount(
        unread=await notification_service.unread_count(db, current.organization_id)
    )


@router.post("/notifications/read_all", response_model=UnreadCount)
async def mark_all_read(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_all_read(db, current.organization_id)
    return UnreadCount(unread=0)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await notification_service.get(
        db, notification_id, current.organization_id
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return await notification_service.mark_read(db, record)
