"""Evaluate orchestrator routing on labelled cases.

A routing case pairs a query with the agent that *should* handle it. Given a
router (e.g. :func:`app.agents.orchestrator.keyword_router`), we measure how
often it routes correctly. Pure and offline — no LLM or database required.
"""

from dataclasses import dataclass
from statistics import mean

from app.agents.orchestrator import Router


@dataclass
class RoutingCase:
    query: str
    expected_agent: str


def evaluate_routing(router: Router, cases: list[RoutingCase]) -> dict:
    per_case = []
    correct = []
    for case in cases:
        chosen = router(case.query)
        hit = chosen == case.expected_agent
        correct.append(1.0 if hit else 0.0)
        per_case.append(
            {
                "query": case.query,
                "expected": case.expected_agent,
                "chosen": chosen,
                "correct": hit,
            }
        )
    return {
        "num_cases": len(cases),
        "accuracy": mean(correct) if correct else 0.0,
        "per_case": per_case,
    }


#: A small labelled set spanning quantitative (sql) and document (research) asks.
ROUTING_CASES = [
    RoutingCase("What was total revenue by region last quarter?", "sql"),
    RoutingCase("How many units did we sell?", "sql"),
    RoutingCase("Compare sales across products", "sql"),
    RoutingCase("Summarise our data retention policy", "research"),
    RoutingCase("What does the documentation say about encryption?", "research"),
    RoutingCase("Explain the onboarding process for new hires", "research"),
]
