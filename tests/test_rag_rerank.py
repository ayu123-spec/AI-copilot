from app.rag.hybrid import RetrievedChunk
from app.rag.rerank import FakeReranker, get_reranker


def _chunks():
    return [
        RetrievedChunk(id="1", score=0.0, text="cats and dogs are household pets"),
        RetrievedChunk(id="2", score=0.0, text="python is a programming language"),
        RetrievedChunk(id="3", score=0.0, text="quarterly cloud revenue grew"),
    ]


def test_fake_reranker_promotes_best_overlap():
    out = FakeReranker().rerank("python programming language", _chunks(), top_n=2)
    assert out[0].id == "2"  # strongest token overlap with the query
    assert len(out) == 2  # trimmed to top_n


def test_reranker_assigns_scores_and_trims():
    out = FakeReranker().rerank("cloud revenue", _chunks(), top_n=1)
    assert len(out) == 1
    assert out[0].id == "3"
    assert out[0].score >= 1.0  # at least the shared tokens "cloud","revenue"


def test_get_reranker_returns_fake_backend():
    r = get_reranker(backend="fake")
    assert isinstance(r, FakeReranker)
