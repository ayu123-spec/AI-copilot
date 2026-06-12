"""Validation for the read-only SQL agent.

Defence in depth: the analytics engine opens every connection with
``PRAGMA query_only = ON`` (writes rejected at the driver level), and this guard
*independently* enforces — before a statement is ever executed — that it is a
single read-only ``SELECT`` over known tables. Either layer alone blocks writes;
together they make a write effectively impossible.
"""

import sqlparse
from sqlparse import tokens as T

#: Keywords that must never appear in a query the agent runs.
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "REINDEX", "EXEC", "EXECUTE", "MERGE", "INTO", "RENAME", "COMMIT",
}  # fmt: skip

_COMMENT_TYPES = (T.Comment, T.Comment.Single, T.Comment.Multiline)


class SqlGuardError(ValueError):
    """Raised when a statement is not a safe, read-only SELECT."""


def _single_statement(sql: str) -> str:
    statements = [s for s in sqlparse.split(sql) if s.strip()]
    if not statements:
        raise SqlGuardError("empty SQL statement")
    if len(statements) > 1:
        raise SqlGuardError("only a single statement is allowed")
    return statements[0]


def _first_keyword(parsed) -> str | None:
    """The first meaningful token value, skipping whitespace, comments and any
    leading open-parenthesis (e.g. a parenthesised subquery)."""
    for tok in parsed.flatten():
        if tok.is_whitespace or tok.ttype in _COMMENT_TYPES:
            continue
        if tok.ttype is T.Punctuation and tok.value == "(":
            continue
        return tok.value.upper()
    return None


def _ensure_no_forbidden(parsed) -> None:
    keyword_types = (T.Keyword, T.DDL, T.DML, T.Keyword.DDL, T.Keyword.DML)
    for tok in parsed.flatten():
        if tok.ttype in keyword_types and tok.value.upper() in FORBIDDEN_KEYWORDS:
            raise SqlGuardError(f"keyword not allowed: {tok.value.upper()}")


def _referenced_tables(parsed) -> set[str]:
    """Best-effort: names appearing immediately after FROM/JOIN. The driver-level
    read-only guarantee does not depend on this; it is an extra allow-list."""
    tables: set[str] = set()
    expecting = False
    for tok in parsed.flatten():
        if tok.is_whitespace or tok.ttype in _COMMENT_TYPES:
            continue
        if tok.ttype is T.Keyword and tok.value.upper() in ("FROM", "JOIN"):
            expecting = True
            continue
        if expecting:
            if tok.ttype is T.Name:
                tables.add(tok.value.strip('"`[]').lower())
            expecting = False
    return tables


def validate_select(sql: str, allowed_tables: set[str]) -> str:
    """Return the single, validated statement or raise :class:`SqlGuardError`."""
    statement = _single_statement(sql)
    parsed = sqlparse.parse(statement)[0]

    if _first_keyword(parsed) not in ("SELECT", "WITH"):
        raise SqlGuardError("only SELECT statements are allowed")

    _ensure_no_forbidden(parsed)

    allowed = {t.lower() for t in allowed_tables}
    unknown = {t for t in _referenced_tables(parsed) if t not in allowed}
    if unknown:
        raise SqlGuardError(f"unknown table(s): {', '.join(sorted(unknown))}")

    return statement.strip().rstrip(";")


def ensure_limit(sql: str, max_rows: int) -> str:
    """Append ``LIMIT max_rows`` if the statement has no LIMIT of its own."""
    has_limit = any(
        tok.ttype is T.Keyword and tok.value.upper() == "LIMIT"
        for tok in sqlparse.parse(sql)[0].flatten()
    )
    if has_limit:
        return sql
    return f"{sql.rstrip().rstrip(';')} LIMIT {max_rows}"
