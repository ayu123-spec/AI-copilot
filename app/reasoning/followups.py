"""Suggested follow-up questions, tailored to the detected query type.

Deterministic and offline (template-based); a real model can later generate
these dynamically behind the same interface.
"""

from __future__ import annotations

from app.insight.classifier import QueryType

_TEMPLATES: dict[QueryType, list[str]] = {
    QueryType.RESUME_ANALYSIS: [
        "What roles should I target with this profile?",
        "How can I quantify my impact more convincingly?",
        "Which skills would most improve my chances?",
    ],
    QueryType.CONTRACT_REVIEW: [
        "Which clauses should I negotiate first?",
        "What are the biggest risks for me here?",
        "What standard protections look missing?",
    ],
    QueryType.COMPARE: [
        "Which option is better for my use case?",
        "What are the cost differences?",
        "How hard is it to switch later?",
    ],
    QueryType.SUMMARY: [
        "What are the most important action items?",
        "What's the single biggest takeaway?",
        "What's missing or unclear?",
    ],
    QueryType.RISK_ASSESSMENT: [
        "Which risk should we address first?",
        "How can we mitigate the top risk?",
        "What early-warning signs should we watch?",
    ],
    QueryType.ROADMAP: [
        "What are the dependencies between phases?",
        "What could delay this plan?",
        "What should we ship first?",
    ],
    QueryType.ACTION_PLAN: [
        "What's the very first step?",
        "What are the quick wins?",
        "What might block progress?",
    ],
    QueryType.RESEARCH: [
        "What does the most recent evidence say?",
        "What are the main counterarguments?",
        "Where are the biggest unknowns?",
    ],
    QueryType.STRATEGIC_ANALYSIS: [
        "What's the recommended option and why?",
        "What are the key risks?",
        "What would competitors likely do?",
    ],
    QueryType.EXPLAIN: [
        "Can you give a concrete example?",
        "How does this compare to the alternatives?",
        "What are common mistakes to avoid?",
    ],
    QueryType.ACADEMIC_REVIEW: [
        "What are the main limitations?",
        "How could the methodology improve?",
        "What follow-up work makes sense?",
    ],
    QueryType.BRAINSTORM: [
        "Which idea is most promising?",
        "How would we validate the top idea?",
        "What's a bolder alternative?",
    ],
}

_DEFAULT = [
    "Can you go deeper on this?",
    "What are the key takeaways?",
    "What should I look at next?",
]


def suggest_followups(query_type: str | QueryType, limit: int = 3) -> list[str]:
    try:
        qt = query_type if isinstance(query_type, QueryType) else QueryType(query_type)
    except ValueError:
        qt = QueryType.GENERAL
    return _TEMPLATES.get(qt, _DEFAULT)[:limit]
