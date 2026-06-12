"""Read-only SQL agent: a seeded analytics database, a guard that enforces
single read-only SELECTs over known tables, the query tool, and the agent."""

from app.agents.sql.agent import SqlAgent
from app.agents.sql.database import (
    ALLOWED_TABLES,
    create_analytics_database,
    metadata,
    read_only_engine,
    schema_description,
)
from app.agents.sql.guard import (
    SqlGuardError,
    ensure_limit,
    validate_select,
)
from app.agents.sql.tool import SqlQueryTool

__all__ = [
    "SqlAgent",
    "SqlQueryTool",
    "SqlGuardError",
    "validate_select",
    "ensure_limit",
    "create_analytics_database",
    "read_only_engine",
    "schema_description",
    "metadata",
    "ALLOWED_TABLES",
]
