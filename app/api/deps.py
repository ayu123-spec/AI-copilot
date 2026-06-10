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
        raise _CREDENTIALS_ERROR
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


def get_vector_store():
    """Vector store dependency. Overridden in tests with an in-memory store."""
    from app.vectorstore.qdrant_store import VectorStore

    return VectorStore()
