"""Query intent classification.

Maps a user's question to a :class:`QueryType`, which selects the reasoning
persona and report structure used to generate the answer. The default
classifier is rule-based — deterministic, offline, and needs no model — so it
runs in tests and without an API key. An LLM-backed classifier can later be
layered behind the same ``classify_query`` interface.
"""

from __future__ import annotations

from enum import Enum


class QueryType(str, Enum):
    """The kind of analysis a question calls for."""

    RESUME_ANALYSIS = "resume_analysis"
    CONTRACT_REVIEW = "contract_review"
    ACADEMIC_REVIEW = "academic_review"
    COMPARE = "compare"
    SUMMARY = "summary"
    RISK_ASSESSMENT = "risk_assessment"
    ROADMAP = "roadmap"
    ACTION_PLAN = "action_plan"
    BRAINSTORM = "brainstorm"
    RESEARCH = "research"
    STRATEGIC_ANALYSIS = "strategic_analysis"
    EXPLAIN = "explain"
    GENERAL = "general"


# Ordered most-specific first; the first rule with a matching keyword wins.
_RULES: list[tuple[QueryType, tuple[str, ...]]] = [
    (
        QueryType.RESUME_ANALYSIS,
        (
            "resume",
            "cv",
            "curriculum vitae",
            "candidate",
            "faang",
            "hireable",
            "hirability",
            "my profile",
            "job application",
            "land a job",
        ),
    ),
    (
        QueryType.CONTRACT_REVIEW,
        (
            "contract",
            "agreement",
            "nda",
            "clause",
            "terms and conditions",
            "liability",
            "indemnif",
            "governing law",
            "termination",
            "lease",
            "msa",
        ),
    ),
    (
        QueryType.ACADEMIC_REVIEW,
        (
            "research paper",
            "the paper",
            "this paper",
            "abstract",
            "methodology",
            "literature review",
            "hypothesis",
            "peer review",
            "the study",
            "this study",
        ),
    ),
    (
        QueryType.RISK_ASSESSMENT,
        (
            "risk",
            "risks",
            "threat",
            "vulnerab",
            "exposure",
            "what could go wrong",
            "downside",
            "failure mode",
            "red flag",
        ),
    ),
    (
        QueryType.ROADMAP,
        (
            "roadmap",
            "timeline",
            "milestone",
            "phased plan",
            "release plan",
            "sequence of",
        ),
    ),
    (
        QueryType.ACTION_PLAN,
        (
            "action plan",
            "step by step",
            "steps to",
            "how do i",
            "how can i",
            "how should i",
            "what should i do",
            "plan to",
            "checklist",
            "next steps",
        ),
    ),
    (
        QueryType.BRAINSTORM,
        (
            "brainstorm",
            "ideas for",
            "ideate",
            "generate ideas",
            "come up with",
            "suggest some",
        ),
    ),
    (
        QueryType.COMPARE,
        (
            "compare",
            "comparison",
            " vs ",
            " vs.",
            "versus",
            "difference between",
            "pros and cons",
            "which is better",
            "trade-off",
            "tradeoff",
        ),
    ),
    (
        QueryType.STRATEGIC_ANALYSIS,
        (
            "strategy",
            "strategic",
            "go to market",
            "go-to-market",
            "positioning",
            "competitive",
            "market analysis",
            "swot",
            "business case",
        ),
    ),
    (
        QueryType.RESEARCH,
        (
            "research",
            "deep dive",
            "investigate",
            "find out",
            "look into",
            "state of the art",
            "current trends",
            "latest on",
        ),
    ),
    (
        QueryType.SUMMARY,
        (
            "summary",
            "summarize",
            "summarise",
            "tl;dr",
            "tldr",
            "key points",
            "key takeaways",
            "main points",
            "overview of",
            "key takeaway",
        ),
    ),
    (
        QueryType.EXPLAIN,
        (
            "explain",
            "what is",
            "what are",
            "how does",
            "how do",
            "why does",
            "why is",
            "define",
            "help me understand",
            "walk me through",
        ),
    ),
]


def classify_query(query: str) -> QueryType:
    """Return the best-matching :class:`QueryType` for ``query``.

    Falls back to :attr:`QueryType.GENERAL` (conversational) when nothing
    matches, so casual chat stays natural rather than being forced into a report.
    """
    # Pad with spaces so word-boundary keywords like " vs " match cleanly.
    q = f" {query.lower().strip()} "
    for qtype, keywords in _RULES:
        if any(kw in q for kw in keywords):
            return qtype
    return QueryType.GENERAL
