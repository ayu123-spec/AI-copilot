from app.chunking.chunkers import (
    Chunk,
    chunk_document,
    fixed_chunks,
    parent_child_chunks,
    recursive_chunks,
    semantic_chunks,
)
from app.embeddings.embedders import FakeEmbedder
from app.ingestion.base import ParsedDocument, ParsedPage

SAMPLE = (
    "Artificial intelligence is transforming industries. "
    "Machine learning models learn from data. "
    "Retrieval augmented generation grounds answers in documents. "
    "Vector databases store embeddings for fast search."
) * 5


def test_fixed_chunks_respect_size():
    chunks = fixed_chunks(SAMPLE, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_recursive_chunks_nonempty_and_bounded():
    chunks = recursive_chunks(SAMPLE, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_parent_child_returns_pairs_with_context():
    pairs = parent_child_chunks(SAMPLE, parent_size=400, child_size=120)
    assert pairs
    for child, parent in pairs:
        assert child.strip()
        assert len(parent) >= len(child)


def test_semantic_chunks_with_fake_embedder():
    chunks = semantic_chunks(SAMPLE, FakeEmbedder(dim=64), threshold=0.5)
    assert chunks
    assert all(c.strip() for c in chunks)


def test_chunk_document_attaches_page_metadata():
    doc = ParsedDocument(
        filename="report.pdf",
        content_type="application/pdf",
        pages=[ParsedPage(1, SAMPLE), ParsedPage(2, SAMPLE)],
    )
    chunks = chunk_document(doc, strategy="recursive", size=200)
    assert all(isinstance(c, Chunk) for c in chunks)
    pages = {c.metadata["page_number"] for c in chunks}
    assert pages == {1, 2}
    assert all(c.metadata["source"] == "report.pdf" for c in chunks)


def test_parent_child_via_document_carries_parent_text():
    doc = ParsedDocument("d.txt", "text/plain", [ParsedPage(1, SAMPLE)])
    chunks = chunk_document(doc, strategy="parent_child", parent_size=400, child_size=120)
    assert all("parent_text" in c.metadata for c in chunks)
