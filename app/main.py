"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import auth, chat, documents, users, workspaces
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base, engine

# Import models so their tables are registered on Base.metadata.
import app.models  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Dev convenience: create tables on startup. Use Alembic migrations in production.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("%s started", settings.PROJECT_NAME)
    yield
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

for r in (auth.router, users.router, workspaces.router, documents.router, chat.router):
    app.include_router(r, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


@app.get("/", tags=["meta"])
async def root():
    return {"service": settings.PROJECT_NAME, "docs": "/docs"}
