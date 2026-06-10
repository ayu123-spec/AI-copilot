"""Business logic for authentication and registration."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import Organization, User, UserRole
from app.schemas.auth import RegisterRequest

logger = get_logger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def register_organization_admin(db: AsyncSession, data: RegisterRequest) -> User:
    """Create a new organization and its first user as ADMIN."""
    if await get_user_by_email(db, data.email):
        raise ValueError("A user with this email already exists")

    org = Organization(name=data.organization_name)
    db.add(org)
    await db.flush()  # assign org.id

    verification_token = secrets.token_urlsafe(32)
    user = User(
        organization_id=org.id,
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.ADMIN,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # In production this is emailed. For Phase 0 we log it so the flow is testable.
    logger.info("Verification token for %s: %s", user.email, verification_token)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def verify_email(db: AsyncSession, token: str) -> bool:
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_verified = True
    user.verification_token = None
    await db.commit()
    return True
