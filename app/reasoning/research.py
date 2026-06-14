"""Deep Research: a multi-step RAG pipeline.

Instead of one retrieve-then-answer pass, this decomposes the question into
sub-questions, retrieves evidence for each, pools and de-duplicates the sources,
then asks the model to synthesize a single structured research report. It reuses
the existing RagEngine for retrieval/reranking and the Insight Engine prompts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.insight.classifier import QueryType, classify_query
from app.insight.prompts import build_system_prompt
from app.rag.engine import Citation, RagEngine, build_context
from app.reasoning.decompose import decompose
from app.reasoning.history import Turn, format_history


@dataclass
class ResearchStep:
    sub_question: str
    sources_found: int


@dataclass
class ResearchResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    query_type: str = QueryType.RESEARCH.value
    steps: list[ResearchStep] = field(default_factory=list)


class DeepResearchEngine:
    def __init__(
        self, engine: RagEngine, *, per_step_k: int = 4, max_sources: int = 12
    ):
        self.engine = engine
        self.per_step_k = per_step_k
        self.max_sources = max_sources

    def research(
        self,
        query: str,
        *,
        where: dict | None = None,
        history: list[Turn] | None = None,
    ) -> ResearchResult:
        qt = classify_query(query)
        sub_questions = decompose(query, qt)

        # Gather evidence per sub-question, preserving order and de-duplicating.
        pooled: dict[str, object] = {}
        ordered: list = []
        steps: list[ResearchStep] = []
        for sq in sub_questions:
            chunks = self.engine.search(sq, where=where, top_n=self.per_step_k)
            steps.append(ResearchStep(sub_question=sq, sources_found=len(chunks)))
            for c in chunks:
                if c.id not in pooled:
                    pooled[c.id] = c
                    ordered.append(c)

        evidence = ordered[: self.max_sources]
        if not evidence:
            return ResearchResult(
                answer=(
                    "I don't have enough information in the documents to research "
                    "that. Try uploading relevant material first."
                ),
                citations=[],
                query_type=qt.value,
                steps=steps,
            )

        context, citations = build_context(evidence)
        system = build_system_prompt(QueryType.RESEARCH)
        sub_list = "\n".join(f"- {s.sub_question}" for s in steps)
        hist = format_history(history or [])
        history_block = f"# Conversation so far\n{hist}\n\n" if hist else ""
        user = (
            f"{history_block}"
            f"# Research task\n{query}\n\n"
            f"# Sub-questions investigated\n{sub_list}\n\n"
            f"# Pooled evidence (from the user's documents)\n{context}\n\n"
            "Synthesize a single, well-structured research report that answers the "
            "task using this evidence and your expert judgment, following your "
            "system instructions. Integrate findings across sources rather than "
            "summarizing each one separately."
        )
        answer = self.engine.generator.generate(system, user)
        return ResearchResult(
            answer=answer, citations=citations, query_type=qt.value, steps=steps
        )
