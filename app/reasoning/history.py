"""Conversation memory helpers.

Turn the stored message history into (a) a compact transcript the model can read
for context, and (b) a richer retrieval query, so a follow-up like "what about
the second one?" still retrieves the right evidence.
"""

from __future__ import annotations

# A turn is (role, content); role is "user" or "assistant".
Turn = tuple[str, str]


def format_history(history: list[Turn], limit: int = 6) -> str:
    """Render the last few turns as 'User:'/'Assistant:' lines for the prompt."""
    recent = history[-limit:] if history else []
    lines = []
    for role, content in recent:
        who = "User" if role == "user" else "Assistant"
        text = content.strip()
        if text:
            lines.append(f"{who}: {text}")
    return "\n".join(lines)


def build_retrieval_query(query: str, history: list[Turn], max_prev: int = 2) -> str:
    """Prepend the last couple of *user* turns to the current query so retrieval
    has the context a terse follow-up omits. Falls back to the query alone."""
    user_turns = [c.strip() for r, c in history if r == "user" and c.strip()]
    prev = user_turns[-max_prev:] if user_turns else []
    combined = " ".join([*prev, query]).strip()
    return combined or query
