"""The tool that actually runs SQL for the SQL agent.

Every statement is run through the guard and given a row cap *before* it touches
the database, then executed on the read-only engine. Failures (guard rejections
or execution errors) are surfaced as :class:`ToolError` so the agent can react
(e.g. revise and retry).
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.agents.sql.guard import SqlGuardError, ensure_limit, validate_select
from app.agents.tools import Tool, ToolError, ToolResult


def _format_rows(columns: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"
    header = " | ".join(columns)
    body = "\n".join(" | ".join(str(r[c]) for c in columns) for r in rows)
    return f"{header}\n{body}"


class SqlQueryTool(Tool):
    name = "sql_query"
    description = (
        "Run a single read-only SQL SELECT against the analytics database and "
        "return the resulting rows. Input: a SQLite SELECT statement."
    )

    def __init__(
        self,
        engine: Engine,
        allowed_tables: set[str],
        *,
        max_rows: int = 100,
    ) -> None:
        self._engine = engine
        self._allowed = {t.lower() for t in allowed_tables}
        self._max_rows = max_rows

    def run(self, **kwargs) -> ToolResult:
        sql = kwargs["sql"]
        try:
            safe = validate_select(sql, self._allowed)
            safe = ensure_limit(safe, self._max_rows)
        except SqlGuardError as exc:
            raise ToolError(f"rejected by SQL guard: {exc}") from exc

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(safe))
                columns = list(result.keys())
                fetched = result.fetchmany(self._max_rows)
        except Exception as exc:
            raise ToolError(f"query failed: {exc}") from exc

        rows = [dict(zip(columns, row, strict=False)) for row in fetched]
        return ToolResult(
            output=_format_rows(columns, rows),
            metadata={"sql": safe, "columns": columns, "rows": rows},
        )
