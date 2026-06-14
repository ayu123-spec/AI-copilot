"""Schemas for the notifications feed."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str | None
    level: str
    title: str
    body: str
    event_type: str
    read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
