"""The Reasoning Engine: conversation memory, contextual retrieval, follow-up
suggestions, and multi-step deep research.

Note: ``research`` (DeepResearchEngine) is intentionally *not* re-exported here —
it imports the RAG engine, which imports this package, so importing it eagerly
would create a cycle. Import it directly: ``from app.reasoning.research import
DeepResearchEngine``.
"""

from app.reasoning.decompose import decompose
from app.reasoning.followups import suggest_followups
from app.reasoning.history import build_retrieval_query, format_history

__all__ = [
    "decompose",
    "suggest_followups",
    "build_retrieval_query",
    "format_history",
]
