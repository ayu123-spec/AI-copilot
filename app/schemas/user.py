"""Pydantic schemas for users and workspaces."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.models.workspace import WorkspaceRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_verified: bool
    created_at: datetime


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceSettingsUpdate(BaseModel):
    upload_limit_mb: int | None = Field(default=None, ge=1, le=10_000)
    storage_quota_mb: int | None = Field(default=None, ge=1)
    agent_permissions: dict | None = None


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    settings: dict
    created_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER
