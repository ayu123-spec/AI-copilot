from app.rag.engine import RagEngine, build_context
from app.rag.hybrid import RetrievedChunk
from app.rag.llm import FakeGenerator
from app.rag.rerank import FakeReranker


def test_build_context_numbers_and_cites():
    chunks = [
        RetrievedChunk(
            id="1",
            score=1.0,
            text="Revenue grew in the cloud.",
            metadata={"source": "q3.pdf", "page_number": 4},
        ),
        RetrievedChunk(
            id="2",
            score=0.5,
            text="Legal reviewed the contract.",
            metadata={"source": "legal.docx"},
        ),
    ]
    context, citations = build_context(chunks)
    assert "[1]" in context and "[2]" in context
    assert "q3.pdf, p.4" in context
    assert citations[0].source == "q3.pdf" and citations[0].page_number == 4
    assert citations[1].page_number is None


class _StubRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    def retrieve(self, query, *, where=None, limit=20):
        return self._chunks


def test_engine_answers_with_citations():
    chunks = [
        RetrievedChunk(
            id="1",
            score=1.0,
            text="The capital is Paris.",
            metadata={"source": "geo.txt", "page_number": 1},
        )
    ]
    engine = RagEngine(_StubRetriever(chunks), FakeReranker(), FakeGenerator())
    ans = engine.answer("What is the capital?", where={"workspace_id": "ws1"})
    assert ans.answer
    assert ans.citations and ans.citations[0].source == "geo.txt"


def test_engine_no_results_says_dont_know():
    engine = RagEngine(_StubRetriever([]), FakeReranker(), FakeGenerator())
    ans = engine.answer("anything", where={"workspace_id": "ws1"})
    assert ans.citations == []
    assert "enough information" in ans.answer.lower()
