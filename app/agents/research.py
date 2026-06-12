"""Research agent.

Gathers evidence from a workspace's documents using the RAG engine, then
synthesises one grounded, cited answer. Retrieval is exposed as a
:class:`RagSearchTool` so the same capability is reusable by the orchestrator.

By default the agent runs a single retrieval hop — fully deterministic and
offline-testable. Set ``max_followups`` > 0 to let it generate refinement
queries and gather evidence across several hops, de-duplicating as it goes.
"""

from app.agents.base import Agent, AgentContext, AgentRun, AgentStep
from app.agents.tools import Tool, ToolResult
from app.rag.engine import SYSTEM_PROMPT, RagEngine, build_context
from app.rag.hybrid import RetrievedChunk
from app.rag.llm import Generator


def _format_evidence(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no matching evidence)"
    lines = []
    for c in chunks:
        src = c.metadata.get("source", "unknown")
        page = c.metadata.get("page_number")
        loc = src + (f", p.{page}" if page else "")
        lines.append(f"- ({loc}) {c.text}")
    return "\n".join(lines)


class RagSearchTool(Tool):
    """Retrieve the most relevant passages from the workspace's documents."""

    name = "rag_search"
    description = (
        "Search the workspace's indexed documents and return the most relevant "
        "passages as evidence. Input: a focused natural-language query."
    )

    def __init__(self, engine: RagEngine, *, top_n: int | None = None) -> None:
        self._engine = engine
        self._top_n = top_n

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        where = kwargs.get("where")
        chunks = self._engine.search(query, where=where, top_n=self._top_n)
        return ToolResult(output=_format_evidence(chunks), metadata={"chunks": chunks})


class ResearchAgent(Agent):
    name = "research"
    description = (
        "Answers questions about the organisation's own documents and knowledge "
        "base by retrieving evidence and synthesising a cited answer."
    )

    def __init__(
        self,
        engine: RagEngine,
        *,
        max_followups: int = 0,
        top_n: int | None = None,
    ) -> None:
        self._engine = engine
        self._generator: Generator = engine.generator
        self._tool = RagSearchTool(engine, top_n=top_n)
        self._max_followups = max_followups

    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        where: dict | None = None
        if context and context.workspace_id:
            where = {"workspace_id": context.workspace_id}

        steps: list[AgentStep] = []
        queries = [query]
        if self._max_followups > 0:
            queries.extend(self._plan_followups(query))

        # Gather evidence across hops, de-duplicated by chunk id (order preserved).
        evidence: list[RetrievedChunk] = []
        seen: set[str] = set()
        for q in queries:
            result = self._tool.run(query=q, where=where)
            hop_chunks: list[RetrievedChunk] = result.metadata["chunks"]
            steps.append(
                AgentStep(
                    thought=f"Retrieve evidence for: {q}",
                    tool=self._tool.name,
                    tool_input={"query": q},
                    observation=f"{len(hop_chunks)} passage(s) found",
                )
            )
            for c in hop_chunks:
                if c.id not in seen:
                    seen.add(c.id)
                    evidence.append(c)

        if not evidence:
            return AgentRun(
                query=query,
                answer=(
                    "I don't have enough information in the documents "
                    "to answer that."
                ),
                steps=steps,
            )

        context_block, citations = build_context(evidence)
        user_prompt = f"Sources:\n{context_block}\n\nQuestion: {query}"
        answer = self._generator.generate(SYSTEM_PROMPT, user_prompt)
        steps.append(
            AgentStep(
                thought="Synthesise a grounded answer from the gathered evidence.",
                observation=f"Answer drafted from {len(citations)} source(s).",
            )
        )
        return AgentRun(query=query, answer=answer, steps=steps, citations=citations)

    def _plan_followups(self, query: str) -> list[str]:
        """Ask the generator for up to ``max_followups`` refinement queries, one
        per line. Any failure or empty output simply yields no follow-ups."""
        system = (
            "You expand a research question into more specific sub-questions. "
            "Return one sub-question per line, with no numbering or extra text."
        )
        try:
            raw = self._generator.generate(system, query)
        except Exception:
            return []
        lines = [ln.strip("-•* \t") for ln in raw.splitlines()]
        followups = [ln for ln in lines if ln and ln.lower() != query.lower()]
        return followups[: self._max_followups]
