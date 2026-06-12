"""Tests for the read-only SQL agent (Phase 3, Part 3)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.agents.sql import (
    ALLOWED_TABLES,
    SqlAgent,
    SqlGuardError,
    SqlQueryTool,
    create_analytics_database,
    ensure_limit,
    read_only_engine,
    schema_description,
    validate_select,
)
from app.agents.tools import ToolError
from app.rag.llm import Generator


@pytest.fixture
def analytics(tmp_path):
    url = f"sqlite:///{tmp_path / 'analytics.db'}"
    create_analytics_database(url)
    engine = read_only_engine(url)
    yield engine
    engine.dispose()


# --------------------------------------------------------------------------- #
# Guard
# --------------------------------------------------------------------------- #
def test_guard_accepts_join_and_aggregate():
    sql = (
        "SELECT p.name, SUM(s.revenue) FROM sales s "
        "JOIN products p ON p.id = s.product_id GROUP BY p.name"
    )
    assert validate_select(sql, ALLOWED_TABLES).startswith("SELECT")


@pytest.mark.parametrize(
    "bad",
    [
        "INSERT INTO products(name) VALUES ('x')",
        "UPDATE products SET unit_price = 0",
        "DELETE FROM sales",
        "DROP TABLE sales",
        "SELECT * FROM sales; DROP TABLE sales",
        "SELECT * FROM users",
        "SELECT * INTO t FROM sales",
        "PRAGMA table_info(sales)",
        "ATTACH DATABASE 'x.db' AS y",
    ],
)
def test_guard_rejects_dangerous_statements(bad):
    with pytest.raises(SqlGuardError):
        validate_select(bad, ALLOWED_TABLES)


def test_ensure_limit_injects_and_preserves():
    assert ensure_limit("SELECT 1", 100).endswith("LIMIT 100")
    assert ensure_limit("SELECT 1 LIMIT 5", 100).endswith("LIMIT 5")


# --------------------------------------------------------------------------- #
# Driver-level read-only enforcement
# --------------------------------------------------------------------------- #
def test_read_only_engine_blocks_writes(analytics):
    with pytest.raises(OperationalError), analytics.connect() as conn:
        conn.execute(text("INSERT INTO regions(id, name) VALUES (99, 'x')"))
        conn.commit()


# --------------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------------- #
def test_sql_tool_executes_select(analytics):
    tool = SqlQueryTool(analytics, ALLOWED_TABLES, max_rows=50)
    result = tool.run(sql="SELECT name FROM products ORDER BY id")
    assert "Copilot Pro" in result.output
    assert result.metadata["rows"][0]["name"] == "Copilot Pro"
    assert "LIMIT" in result.metadata["sql"]  # cap injected


def test_sql_tool_rejects_forbidden(analytics):
    tool = SqlQueryTool(analytics, ALLOWED_TABLES)
    with pytest.raises(ToolError, match="guard"):
        tool.run(sql="DROP TABLE sales")


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
class _SqlStub(Generator):
    """Returns SQL for draft calls and a fixed summary for the summary call.

    The summary prompt is the one whose user message contains 'Results:'.
    """

    def __init__(self, first_sql, retry_sql=None, summary="Here is the answer."):
        self.first_sql = first_sql
        self.retry_sql = retry_sql
        self.summary = summary

    def generate(self, system, user):
        if "Results:" in user:
            return self.summary
        if "previous attempt failed" in user and self.retry_sql is not None:
            return self.retry_sql
        return self.first_sql


def test_sql_agent_answers_question(analytics):
    tool = SqlQueryTool(analytics, ALLOWED_TABLES)
    gen = _SqlStub("SELECT name FROM products ORDER BY id", summary="Three products.")
    run = SqlAgent(gen, tool, schema_description()).run("What products exist?")
    assert run.answer == "Three products."
    assert run.metadata["sql"].upper().startswith("SELECT")
    assert run.metadata["rows"]
    assert any(s.tool == "sql_query" for s in run.steps)


def test_sql_agent_revises_after_rejection(analytics):
    tool = SqlQueryTool(analytics, ALLOWED_TABLES)
    gen = _SqlStub(
        "SELECT * FROM users",  # unknown table -> guard rejects
        retry_sql="SELECT name FROM products",
        summary="ok",
    )
    run = SqlAgent(gen, tool, schema_description(), max_attempts=2).run("list products")
    assert run.answer == "ok"
    assert "products" in run.metadata["sql"]
    assert any(s.observation and "guard" in s.observation for s in run.steps)
