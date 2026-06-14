"""Notification service: persist an in-app notification, fan it out to the
configured outbound channel, and read/mark the feed — all org-scoped."""

import contextlib

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import NotificationRecord
from app.notifications.base import Notification
from app.notifications.factory import get_notifier


async def create(
    db: AsyncSession,
    *,
    organization_id: str,
    workspace_id: str | None = None,
    title: str,
    body: str = "",
    level: str = "info",
    event_type: str = "general",
) -> NotificationRecord | None:
    """Persist an in-app notification and best-effort deliver it outbound.

    The caller's transaction is responsible for committing the record.
    """
    if not settings.NOTIFICATIONS_ENABLED:
        return None

    record = NotificationRecord(
        organization_id=organization_id,
        workspace_id=workspace_id,
        title=title[:255],
        body=body,
        level=level,
        event_type=event_type,
    )
    db.add(record)
    await db.flush()

    # Outbound delivery is best-effort and must never break the request.
    with contextlib.suppress(Exception):
        get_notifier().notify(
            Notification(title=title, body=body, level=level, event_type=event_type)
        )

    return record


async def list_notifications(
    db: AsyncSession,
    organization_id: str,
    workspace_id: str | None = None,
    limit: int = 50,
) -> list[NotificationRecord]:
    stmt = select(NotificationRecord).where(
        NotificationRecord.organization_id == organization_id
    )
    if workspace_id:
        stmt = stmt.where(NotificationRecord.workspace_id == workspace_id)
    stmt = stmt.order_by(NotificationRecord.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def unread_count(db: AsyncSession, organization_id: str) -> int:
    stmt = select(func.count(NotificationRecord.id)).where(
        NotificationRecord.organization_id == organization_id,
        NotificationRecord.read.is_(False),
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def get(
    db: AsyncSession, notification_id: str, organization_id: str
) -> NotificationRecord | None:
    stmt = select(NotificationRecord).where(
        NotificationRecord.id == notification_id,
        NotificationRecord.organization_id == organization_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def mark_read(db: AsyncSession, record: NotificationRecord) -> NotificationRecord:
    record.read = True
    await db.commit()
    await db.refresh(record)
    return record


async def mark_all_read(db: AsyncSession, organization_id: str) -> None:
    await db.execute(
        update(NotificationRecord)
        .where(
            NotificationRecord.organization_id == organization_id,
            NotificationRecord.read.is_(False),
        )
        .values(read=True)
    )
    await db.commit()
