"""Tests for agent routing evaluation (Phase 3, Part 6)."""

from app.agents.orchestrator import keyword_router
from app.evaluation.agent_eval import ROUTING_CASES, RoutingCase, evaluate_routing


def test_routing_eval_scores_keyword_router():
    m = evaluate_routing(keyword_router, ROUTING_CASES)
    assert m["num_cases"] == len(ROUTING_CASES)
    assert m["accuracy"] >= 0.8  # the keyword router should get most of these right
    assert len(m["per_case"]) == m["num_cases"]


def test_routing_eval_perfect_on_clear_cases():
    cases = [
        RoutingCase("total revenue", "sql"),
        RoutingCase("explain the policy", "research"),
    ]
    assert evaluate_routing(keyword_router, cases)["accuracy"] == 1.0
