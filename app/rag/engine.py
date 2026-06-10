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
        citations.append(Citation(index=i, source=source, page_number=page, text=c.text))
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

    def answer(self, query: str, *, where: dict | None = None) -> RagAnswer:
        candidates = self.retriever.retrieve(query, where=where, limit=self.candidate_k)
        reranked = self.reranker.rerank(query, candidates, top_n=self.top_n)
        if not reranked:
            return RagAnswer(
                answer="I don't have enough information in the documents to answer that.",
                citations=[],
            )
        context, citations = build_context(reranked)
        user_prompt = f"Sources:\n{context}\n\nQuestion: {query}"
        answer_text = self.generator.generate(SYSTEM_PROMPT, user_prompt)
        return RagAnswer(answer=answer_text, citations=citations)
