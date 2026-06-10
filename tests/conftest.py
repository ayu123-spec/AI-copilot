"""Test fixtures: isolated in-memory async DB and an httpx client."""
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
    from app.api.deps import (
        get_embedder,
        get_generator,
        get_reranker,
        get_vector_store,
    )
    from app.embeddings.embedders import FakeEmbedder
    from app.rag.llm import FakeGenerator
    from app.rag.rerank import FakeReranker
    from app.vectorstore.qdrant_store import VectorStore

    fake_embedder = FakeEmbedder(dim=384)
    memory_store = VectorStore(collection="test_docs", location=":memory:")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedder] = lambda: fake_embedder
    app.dependency_overrides[get_vector_store] = lambda: memory_store
    app.dependency_overrides[get_reranker] = lambda: FakeReranker()
    app.dependency_overrides[get_generator] = lambda: FakeGenerator()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
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
