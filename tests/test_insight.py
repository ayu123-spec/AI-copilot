"""Tests for the Insight Engine — query classification, expert prompt building,
and end-to-end wiring into the RAG engine."""

from app.insight.classifier import QueryType, classify_query
from app.insight.prompts import build_system_prompt, build_user_prompt
from app.rag.engine import RagEngine
from app.rag.hybrid import RetrievedChunk
from app.rag.llm import Generator
from app.rag.rerank import FakeReranker


def test_classifier_routes_common_intents():
    assert classify_query("Analyze my resume") is QueryType.RESUME_ANALYSIS
    assert classify_query("How can I improve my chances at FAANG?") is (
        QueryType.RESUME_ANALYSIS
    )
    assert classify_query("Review this contract for red flags") is (
        QueryType.CONTRACT_REVIEW
    )
    assert classify_query("Compare Postgres vs MongoDB") is QueryType.COMPARE
    assert classify_query("Summarize the key takeaways") is QueryType.SUMMARY
    assert classify_query("What are the risks in this plan?") is (
        QueryType.RISK_ASSESSMENT
    )
    assert classify_query("Explain how embeddings work") is QueryType.EXPLAIN
    assert classify_query("Give me an action plan to ship this") is (
        QueryType.ACTION_PLAN
    )


def test_classifier_defaults_to_general_for_casual_chat():
    assert classify_query("hey there, how are you?") is QueryType.GENERAL
    assert classify_query("thanks!") is QueryType.GENERAL


def test_system_prompt_has_persona_and_structure():
    prompt = build_system_prompt(QueryType.RESUME_ANALYSIS)
    assert "recruiter" in prompt.lower()
    assert "Strengths" in prompt
    assert "Recommended Improvements" in prompt
    assert "[1]" in prompt  # citation instruction present


def test_general_prompt_is_conversational_not_a_report():
    prompt = build_system_prompt(QueryType.GENERAL)
    assert "conversationally" in prompt.lower()
    assert "Executive Summary" not in prompt


def test_user_prompt_embeds_question_and_sources():
    up = build_user_prompt("What is X?", "[1] (from a.pdf)\nsome text")
    assert "What is X?" in up
    assert "a.pdf" in up


class _StubRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    def retrieve(self, query, *, where=None, limit=20):
        return self._chunks


class _CapturingGenerator(Generator):
    """Records the prompts it receives so tests can assert what was sent."""

    def __init__(self):
        self.system = ""
        self.user = ""

    def generate(self, system: str, user: str) -> str:
        self.system = system
        self.user = user
        return "Analysis with a citation [1]."


def test_engine_uses_expert_prompt_and_reports_query_type():
    chunks = [
        RetrievedChunk(
            id="1",
            score=1.0,
            text="Skilled in Python, SQL, and built ML projects.",
            metadata={"source": "resume.pdf", "page_number": 1},
        )
    ]
    gen = _CapturingGenerator()
    engine = RagEngine(_StubRetriever(chunks), FakeReranker(), gen)
    ans = engine.answer("Analyze my resume", where={"workspace_id": "ws1"})

    # The query was classified and surfaced.
    assert ans.query_type == QueryType.RESUME_ANALYSIS.value
    # The expert persona + structure reached the model, not the generic prompt.
    assert "recruiter" in gen.system.lower()
    assert "Strengths" in gen.system
    # The user prompt carried the retrieved source.
    assert "resume.pdf" in gen.user
    assert ans.citations and ans.citations[0].source == "resume.pdf"
