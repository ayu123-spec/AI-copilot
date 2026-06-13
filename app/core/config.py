"""Central application configuration, loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Enterprise AI Knowledge Copilot"
    API_V1_PREFIX: str = "/api/v1"

    # Database. Async drivers: postgresql+asyncpg (prod) or sqlite+aiosqlite (dev/test).
    DATABASE_URL: str = "sqlite+aiosqlite:///./copilot.db"

    # Auth / JWT. Override JWT_SECRET in every real environment.
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Workspace defaults
    DEFAULT_UPLOAD_LIMIT_MB: int = 50
    DEFAULT_STORAGE_QUOTA_MB: int = 5000

    # Embeddings: backend is "local" (sentence-transformers), "openai", or "fake".
    EMBEDDING_BACKEND: str = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"  # 384-dim, light to download
    OPENAI_API_KEY: str | None = None

    # Vector store. If QDRANT_URL is unset, an embedded on-disk store is used.
    QDRANT_URL: str | None = None
    QDRANT_PATH: str = "./qdrant_storage"
    QDRANT_COLLECTION: str = "documents"

    # Chunking defaults
    CHUNK_STRATEGY: str = "recursive"

    # Re-ranking: "cross_encoder" (sentence-transformers) or "fake" (offline/tests)
    RERANK_BACKEND: str = "cross_encoder"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Answer generation: "anthropic" (Claude), "openai", or "fake" (offline/tests)
    LLM_BACKEND: str = "fake"
    LLM_MODEL: str = ""  # blank = use the backend's default model
    ANTHROPIC_API_KEY: str | None = None

    # Read-only analytics database for the SQL agent (separate from the app DB).
    ANALYTICS_DATABASE_URL: str = "sqlite:///./analytics.db"
    SQL_AGENT_MAX_ROWS: int = 100

    # Agent memory: long-term semantic recall (Qdrant) + short-term history.
    MEMORY_COLLECTION: str = "memory"
    MEMORY_RECALL_LIMIT: int = 5
    MEMORY_HISTORY_LIMIT: int = 10

    # Knowledge graph (Phase 4). Backend "memory" (in-process; default + tests)
    # or "neo4j" (real server). Entity extractor "rule" (offline) or "llm".
    GRAPH_BACKEND: str = "memory"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str | None = None
    GRAPH_ENTITY_EXTRACTOR: str = "rule"
    GRAPH_MAX_HOPS: int = 2

    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
