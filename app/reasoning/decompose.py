"""Break a complex question into focused sub-questions for multi-step research.

Offline and deterministic: first try to split genuinely compound questions, then
fall back to angle templates chosen by the query type, then to the question
itself. A real model can replace this behind the same ``decompose`` interface.
"""

from __future__ import annotations

import re

from app.insight.classifier import QueryType, classify_query

_ANGLES: dict[QueryType, list[str]] = {
    QueryType.RESUME_ANALYSIS: [
        "What are the candidate's strongest qualifications and achievements?",
        "What gaps, weaknesses, or missing signals stand out?",
        "How does this profile compare to expectations for the target roles?",
    ],
    QueryType.STRATEGIC_ANALYSIS: [
        "What is the current situation and the key facts?",
        "What are the main strategic options?",
        "What are the risks and trade-offs of each option?",
    ],
    QueryType.RISK_ASSESSMENT: [
        "What are the most significant risks present?",
        "What is the likelihood and impact of each risk?",
        "How can the most serious risks be mitigated?",
    ],
    QueryType.COMPARE: [
        "What are the key characteristics of each option?",
        "Where do the options differ most?",
        "Which option fits which use case?",
    ],
    QueryType.CONTRACT_REVIEW: [
        "What are the key terms and obligations?",
        "What risks or unfavorable clauses are present?",
        "What protections appear missing or unclear?",
    ],
    QueryType.RESEARCH: [
        "What are the key facts and findings?",
        "What evidence supports or contradicts them?",
        "What remains uncertain or unanswered?",
    ],
}


def decompose(
    query: str, query_type: QueryType | None = None, max_sub: int = 4
) -> list[str]:
    qt = query_type or classify_query(query)

    # 1) Genuinely compound question? Split on question marks / conjunctions.
    parts = [p.strip(" ,.") for p in re.split(r"\?|\band\b|;|\bvs\.?\b", query)]
    parts = [p for p in parts if len(p) > 12]
    if len(parts) >= 2:
        return [(p if p.endswith("?") else p + "?") for p in parts][:max_sub]

    # 2) Angle templates for this kind of question.
    angles = _ANGLES.get(qt)
    if angles:
        return angles[:max_sub]

    # 3) Nothing to decompose — research the question directly.
    return [query]
