"""Test fixtures: isolated in-memory async DB and an httpx client."""

import shutil
import tempfile
import warnings

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app  # importing main also registers all model tables

# Silence a harmless import-time PendingDeprecationWarning from langgraph's
# checkpoint serde so test output stays clean (registered before any test
# module imports langgraph).
warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change",
)


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    # Phase 1: use a deterministic offline embedder and an ephemeral vector store
    # so document/search tests run without model downloads or a Qdrant server.
    from app.agents.sql import create_analytics_database, read_only_engine
    from app.api.deps import (
        get_analytics_engine,
        get_embedder,
        get_generator,
        get_graph_store,
        get_memory_store,
        get_reranker,
        get_vector_store,
    )
    from app.embeddings.embedders import FakeEmbedder
    from app.graph.memory_store import InMemoryGraphStore
    from app.rag.llm import FakeGenerator
    from app.rag.rerank import FakeReranker
    from app.vectorstore.qdrant_store import VectorStore

    fake_embedder = FakeEmbedder(dim=384)
    docs_store = VectorStore(collection="test_docs", location=":memory:")
    mem_store = VectorStore(collection="test_memory", location=":memory:")
    graph_store = InMemoryGraphStore()

    analytics_dir = tempfile.mkdtemp()
    analytics_url = f"sqlite:///{analytics_dir}/analytics.db"
    create_analytics_database(analytics_url)
    analytics_engine = read_only_engine(analytics_url)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedder] = lambda: fake_embedder
    app.dependency_overrides[get_vector_store] = lambda: docs_store
    app.dependency_overrides[get_memory_store] = lambda: mem_store
    app.dependency_overrides[get_graph_store] = lambda: graph_store
    app.dependency_overrides[get_analytics_engine] = lambda: analytics_engine
    app.dependency_overrides[get_reranker] = lambda: FakeReranker()
    app.dependency_overrides[get_generator] = lambda: FakeGenerator()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    analytics_engine.dispose()
    shutil.rmtree(analytics_dir, ignore_errors=True)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """A standalone in-memory async session for unit-testing services."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def register_and_login(client, email, org="Acme") -> dict:
    """Helper: register an org admin and return auth headers + user payload."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Test User",
            "organization_name": org,
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "user": reg.json()}
