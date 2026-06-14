import io

from app.rag.engine import RagEngine
from app.rag.hybrid import RetrievedChunk
from app.rag.llm import Generator
from app.rag.rerank import FakeReranker
from app.reasoning.decompose import decompose
from app.reasoning.followups import suggest_followups
from app.reasoning.history import build_retrieval_query, format_history
from app.reasoning.research import DeepResearchEngine
from tests.conftest import register_and_login


# ---- unit: memory helpers ----
def test_format_history_renders_and_limits():
    hist = [("user", "hi"), ("assistant", "hello"), ("user", "more")]
    out = format_history(hist, limit=2)
    assert "Assistant: hello" in out and "User: more" in out
    assert "hi" not in out  # trimmed by the limit


def test_build_retrieval_query_uses_prior_user_turns():
    hist = [("user", "Tell me about Postgres"), ("assistant", "It's a database.")]
    q = build_retrieval_query("what about its licensing?", hist)
    assert "Postgres" in q and "licensing" in q
    assert build_retrieval_query("standalone", []) == "standalone"


# ---- unit: follow-ups + decomposition ----
def test_suggest_followups_by_type():
    fu = suggest_followups("resume_analysis")
    assert len(fu) == 3 and any("roles" in f.lower() for f in fu)
    assert len(suggest_followups("not_a_type")) == 3  # safe default


def test_decompose_compound_and_templated():
    compound = decompose("What are the strengths and what are the weaknesses?")
    assert len(compound) >= 2
    templated = decompose("Analyze my resume")  # resume -> angle templates
    assert len(templated) >= 2


# ---- unit: engine memory + deep research ----
class _StubRetriever:
    def __init__(self, chunks):
        self._chunks = chunks
        self.queries: list[str] = []

    def retrieve(self, query, *, where=None, limit=20):
        self.queries.append(query)
        return self._chunks


class _CapturingGenerator(Generator):
    def __init__(self):
        self.system = ""
        self.user = ""

    def generate(self, system: str, user: str) -> str:
        self.system = system
        self.user = user
        return "Synthesized answer [1]."


def _chunks():
    return [
        RetrievedChunk(
            id="c1",
            score=1.0,
            text="Alpha fact.",
            metadata={"source": "a.pdf", "page_number": 1},
        ),
        RetrievedChunk(
            id="c2",
            score=0.8,
            text="Beta fact.",
            metadata={"source": "a.pdf", "page_number": 2},
        ),
    ]


def test_engine_uses_conversation_history():
    gen = _CapturingGenerator()
    stub = _StubRetriever(_chunks())
    engine = RagEngine(stub, FakeReranker(), gen)
    history = [
        ("user", "Tell me about Paris"),
        ("assistant", "Paris is the capital of France."),
    ]
    engine.answer(
        "what about its population?", where={"workspace_id": "w"}, history=history
    )
    assert "Conversation so far" in gen.user
    assert "Paris is the capital" in gen.user
    # Contextual retrieval folded the earlier user turn into the search query.
    assert any("Tell me about Paris" in q for q in stub.queries)


def test_deep_research_decomposes_and_synthesizes():
    gen = _CapturingGenerator()
    stub = _StubRetriever(_chunks())
    engine = RagEngine(stub, FakeReranker(), gen)
    dre = DeepResearchEngine(engine, per_step_k=2)
    res = dre.research(
        "Give me a strategic analysis of our market", where={"workspace_id": "w"}
    )
    assert len(res.steps) >= 2  # decomposed into sub-questions
    assert res.citations  # evidence pooled across steps
    assert "Sub-questions investigated" in gen.user
    assert "Key Findings" in gen.system  # research report structure


# ---- API ----
async def _ws(client, headers):
    return (
        await client.post("/api/v1/workspaces", json={"name": "KB"}, headers=headers)
    ).json()["id"]


async def test_chat_returns_followups_and_grounding(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _ws(client, ctx["headers"])
    files = {
        "file": ("q.txt", io.BytesIO(b"Revenue grew on cloud services."), "text/plain")
    }
    await client.post(
        f"/api/v1/workspaces/{ws}/documents", files=files, headers=ctx["headers"]
    )
    res = await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={"query": "Summarize the key takeaways"},
        headers=ctx["headers"],
    )
    body = res.json()
    assert body["follow_ups"]
    assert body["grounding"] in ("grounded", "partial", "ungrounded")


async def test_deep_research_mode_returns_steps(client):
    ctx = await register_and_login(client, "admin@acme.com")
    ws = await _ws(client, ctx["headers"])
    res = await client.post(
        f"/api/v1/workspaces/{ws}/chat",
        json={
            "query": "Give a strategic analysis of the market",
            "deep_research": True,
        },
        headers=ctx["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body["research_steps"], list)
    assert len(body["research_steps"]) >= 1
    assert body["follow_ups"]
