"""The SQL agent.

Turns a natural-language question into a read-only SQL query over the analytics
database, runs it through :class:`SqlQueryTool` (guarded + capped), and
summarises the rows in plain language. If a draft is rejected or errors, the
agent feeds the error back to the model and tries again, up to ``max_attempts``.
The generated SQL is always returned in the run metadata for transparency.
"""

from app.agents.base import Agent, AgentContext, AgentRun, AgentStep
from app.agents.sql.tool import SqlQueryTool
from app.agents.tools import ToolError
from app.rag.llm import Generator

_DRAFT_GUIDANCE = (
    "You translate the user's question into ONE read-only SQLite SELECT query. "
    "Use only the tables and columns in the schema below. Never write INSERT, "
    "UPDATE, DELETE, or DDL. Return only the SQL, with no explanation or code "
    "fences.\n\nSchema:\n"
)

_SUMMARY_SYSTEM = (
    "You answer the user's question using ONLY the SQL query results provided. "
    "Be concise and quote the relevant numbers."
)


def _extract_sql(raw: str) -> str:
    """Strip code fences / a leading 'sql' label the model might add."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:3].lower() == "sql":
            text = text[3:]
    return text.strip()


class SqlAgent(Agent):
    name = "sql"
    description = (
        "Answers quantitative questions about sales, products and regions by "
        "querying the structured analytics database with read-only SQL."
    )

    def __init__(
        self,
        generator: Generator,
        tool: SqlQueryTool,
        schema: str,
        *,
        max_attempts: int = 2,
    ) -> None:
        self._gen = generator
        self._tool = tool
        self._schema = schema
        self._max_attempts = max_attempts

    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        steps: list[AgentStep] = []
        error: str | None = None

        for attempt in range(1, self._max_attempts + 1):
            sql = self._draft_sql(query, error)
            steps.append(
                AgentStep(thought=f"Draft SQL (attempt {attempt}).", observation=sql)
            )
            try:
                result = self._tool.run(sql=sql)
            except ToolError as exc:
                error = str(exc)
                steps.append(
                    AgentStep(
                        thought="Query rejected or failed; revise and retry.",
                        tool=self._tool.name,
                        tool_input={"sql": sql},
                        observation=error,
                    )
                )
                continue

            steps.append(
                AgentStep(
                    tool=self._tool.name,
                    tool_input={"sql": result.metadata["sql"]},
                    observation=f"{len(result.metadata['rows'])} row(s) returned",
                )
            )
            answer = self._summarise(query, result.metadata["sql"], result.output)
            return AgentRun(
                query=query,
                answer=answer,
                steps=steps,
                metadata={
                    "sql": result.metadata["sql"],
                    "rows": result.metadata["rows"],
                },
            )

        return AgentRun(
            query=query,
            answer=f"I couldn't answer that from the analytics database. ({error})",
            steps=steps,
            metadata={"error": error},
        )

    def _draft_sql(self, query: str, error: str | None) -> str:
        system = _DRAFT_GUIDANCE + self._schema
        if error:
            user = (
                f"{query}\n\nThe previous attempt failed: {error}\n"
                "Write a corrected query."
            )
        else:
            user = query
        return _extract_sql(self._gen.generate(system, user))

    def _summarise(self, query: str, sql: str, results: str) -> str:
        user = f"Question: {query}\n\nSQL: {sql}\n\nResults:\n{results}"
        return self._gen.generate(_SUMMARY_SYSTEM, user)
