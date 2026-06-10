"""Persistence for chat history and feedback, scoped to the caller's org."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole


async def create_conversation(
    db: AsyncSession, org_id: str, workspace_id: str, title: str
) -> Conversation:
    conv = Conversation(
        organization_id=org_id, workspace_id=workspace_id, title=title[:255] or "New conversation"
    )
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation(
    db: AsyncSession, conversation_id: str, org_id: str
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def add_message(
    db: AsyncSession,
    conversation_id: str,
    role: MessageRole,
    content: str,
    citations: list | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations or [],
    )
    db.add(msg)
    await db.flush()
    return msg


async def list_conversations(
    db: AsyncSession, org_id: str, workspace_id: str
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.organization_id == org_id,
            Conversation.workspace_id == workspace_id,
        )
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def list_messages(db: AsyncSession, conversation_id: str) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def get_message(db: AsyncSession, message_id: str, org_id: str) -> Message | None:
    """Fetch a message only if its conversation belongs to the caller's org."""
    result = await db.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.id == message_id, Conversation.organization_id == org_id)
    )
    return result.scalar_one_or_none()


async def set_feedback(db: AsyncSession, message: Message, rating: str) -> Message:
    message.feedback = rating
    await db.commit()
    await db.refresh(message)
    return message
