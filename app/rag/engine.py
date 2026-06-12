"""The RAG engine: ties retrieval, re-ranking, citation building, and generation
into a single grounded, cited answer."""

from dataclasses import dataclass, field

from app.rag.hybrid import HybridRetriever, RetrievedChunk
from app.rag.llm import Generator
from app.rag.rerank import Reranker

SYSTEM_PROMPT = (
    "You are a precise assistant. Answer the question using ONLY the numbered "
    "sources provided. Cite the sources you rely on inline with their number, "
    "like [1] or [2]. If the answer is not contained in the sources, say you do "
    "not have enough information."
)


@dataclass
class Citation:
    index: int
    source: str
    page_number: int | None
    text: str


@dataclass
class RagAnswer:
    answer: str
    citations: list[Citation] = field(default_factory=list)


def build_context(chunks: list[RetrievedChunk]) -> tuple[str, list[Citation]]:
    """Number the chunks, build the context block the LLM sees, and the matching
    citation list returned to the caller."""
    citations: list[Citation] = []
    blocks: list[str] = []
    for i, c in enumerate(chunks, start=1):
        source = c.metadata.get("source", "unknown")
        page = c.metadata.get("page_number")
        citations.append(
            Citation(index=i, source=source, page_number=page, text=c.text)
        )
        loc = source + (f", p.{page}" if page else "")
        blocks.append(f"[{i}] (from {loc})\n{c.text}")
    return "\n\n".join(blocks), citations


class RagEngine:
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker,
        generator: Generator,
        *,
        candidate_k: int = 20,
        top_n: int = 5,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.candidate_k = candidate_k
        self.top_n = top_n

    def search(
        self, query: str, *, where: dict | None = None, top_n: int | None = None
    ) -> list[RetrievedChunk]:
        """Retrieve and re-rank evidence for a query *without* generating an
        answer. Lets agents gather evidence across several queries before
        synthesising once."""
        candidates = self.retriever.retrieve(query, where=where, limit=self.candidate_k)
        n = self.top_n if top_n is None else top_n
        return self.reranker.rerank(query, candidates, top_n=n)

    def _retrieve(self, query: str, where: dict | None):
        return self.search(query, where=where)

    def answer(self, query: str, *, where: dict | None = None) -> RagAnswer:
        reranked = self._retrieve(query, where)
        if not reranked:
            return RagAnswer(
                answer=(
                    "I don't have enough information in the documents "
                    "to answer that."
                ),
                citations=[],
            )
        context, citations = build_context(reranked)
        user_prompt = f"Sources:\n{context}\n\nQuestion: {query}"
        answer_text = self.generator.generate(SYSTEM_PROMPT, user_prompt)
        return RagAnswer(answer=answer_text, citations=citations)

    def stream(self, query: str, *, where: dict | None = None):
        """Return (citations, token_iterator). Citations are known up front;
        the answer text streams token by token."""
        reranked = self._retrieve(query, where)
        if not reranked:
            return [], iter(
                ["I don't have enough information in the documents to answer that."]
            )
        context, citations = build_context(reranked)
        user_prompt = f"Sources:\n{context}\n\nQuestion: {query}"
        return citations, self.generator.stream(SYSTEM_PROMPT, user_prompt)
