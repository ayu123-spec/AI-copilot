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

    # Insight Engine: classify the query and answer with an expert persona +
    # structured report instead of generic source regurgitation.
    INSIGHT_ENGINE_ENABLED: bool = True

    # Notifications: in-app feed (always on) + one outbound channel.
    # NOTIFICATION_CHANNEL: "console" (default) | "memory" | "slack" | "teams" | "email"
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_CHANNEL: str = "console"
    NOTIFICATION_MIN_LEVEL: str = "info"
    SLACK_WEBHOOK_URL: str | None = None
    TEAMS_WEBHOOK_URL: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    NOTIFICATION_EMAIL_FROM: str | None = None
    NOTIFICATION_EMAIL_TO: str | None = None

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

    # Multimodal RAG: describe images so they become retrievable text.
    IMAGE_DESCRIBER_BACKEND: str = "fake"  # "fake" | "anthropic"
    VISION_MODEL: str = "claude-3-5-sonnet-20241022"

    # Guardrails: input/output safety for the chat + agent path.
    GUARDRAILS_ENABLED: bool = True
    GUARDRAIL_BLOCK_INJECTION: bool = True
    GUARDRAIL_REDACT_PII: bool = True
    GUARDRAIL_REDACT_PII_IN_INPUT: bool = False
    GUARDRAIL_MIN_FAITHFULNESS: float = 0.0  # 0 disables the grounding check
    GUARDRAIL_TOXICITY_DENYLIST: list[str] = []

    # CORS: origins allowed to call the API from a browser (the React dev app).
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
