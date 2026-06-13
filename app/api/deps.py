"""Shared API dependencies: authentication and role-based authorization."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.models.user import User, UserRole

_bearer = HTTPBearer(auto_error=True)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR from None
    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR
    user_id = payload.get("sub")
    if not user_id:
        raise _CREDENTIALS_ERROR
    user = await db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR
    return user


def require_roles(*roles: UserRole):
    """Dependency factory enforcing that the current user holds one of `roles`."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker


def get_embedder():
    """Embedder dependency. Overridden in tests with a fake embedder."""
    from app.embeddings.embedders import get_embedder as _get

    return _get()


_vector_store = None


def get_vector_store():
    """Vector store dependency (singleton — avoids re-opening the embedded store).
    Overridden in tests with an in-memory store."""
    global _vector_store
    if _vector_store is None:
        from app.vectorstore.qdrant_store import VectorStore

        _vector_store = VectorStore()
    return _vector_store


_reranker = None


def get_reranker():
    """Re-ranker dependency (singleton — loads any model once). Overridden in tests."""
    global _reranker
    if _reranker is None:
        from app.rag.rerank import get_reranker as _get

        _reranker = _get()
    return _reranker


_generator = None


def get_generator():
    """LLM generator dependency (singleton — one client). Overridden in tests."""
    global _generator
    if _generator is None:
        from app.rag.llm import get_generator as _get

        _generator = _get()
    return _generator


_memory_store = None


def get_memory_store():
    """Long-term memory vector store (singleton). Overridden in tests with an
    in-memory store."""
    global _memory_store
    if _memory_store is None:
        from app.core.config import settings
        from app.vectorstore.qdrant_store import VectorStore

        _memory_store = VectorStore(collection=settings.MEMORY_COLLECTION)
    return _memory_store


_analytics_engine = None


def get_analytics_engine():
    """Read-only analytics engine for the SQL agent (singleton). Ensures the
    sample database exists and is seeded. Overridden in tests."""
    global _analytics_engine
    if _analytics_engine is None:
        from app.agents.sql import create_analytics_database, read_only_engine
        from app.core.config import settings

        create_analytics_database(settings.ANALYTICS_DATABASE_URL)
        _analytics_engine = read_only_engine(settings.ANALYTICS_DATABASE_URL)
    return _analytics_engine
