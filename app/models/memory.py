"""Long-term agent memory.

A :class:`MemoryItem` is the durable, relational record of something worth
remembering across conversations (a fact, preference, or summary), scoped to an
organization and workspace. The DB row is the source of truth; the same content
is embedded into the Qdrant memory collection for semantic recall.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class MemoryKind(str, enum.Enum):
    NOTE = "note"
    FACT = "fact"
    PREFERENCE = "preference"
    SUMMARY = "summary"


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), nullable=False, index=True
    )
    kind: Mapped[MemoryKind] = mapped_column(
        Enum(MemoryKind), default=MemoryKind.NOTE, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
