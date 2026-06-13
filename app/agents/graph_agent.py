"""Graph agent (GraphRAG).

Answers relationship and multi-hop questions by fusing two sources: facts
traversed from the knowledge graph and passages retrieved from the vector store.
The graph supplies the structural answer ("who reports to whom"); the documents
supply supporting detail and citations. Tenant scoping comes from the
:class:`AgentContext`, and long-term memories are folded in just as the research
agent does.
"""

from app.agents.base import Agent, AgentContext, AgentRun, AgentStep
from app.agents.research import _context_preamble
from app.graph.retriever import GraphRetriever
from app.rag.engine import SYSTEM_PROMPT, RagEngine, build_context


class GraphAgent(Agent):
    name = "graph"
    description = (
        "Answers questions about how entities relate — people, teams, companies, "
        "projects — such as who reports to or manages whom, org structure, and "
        "other multi-hop relationship questions, using a knowledge graph."
    )

    def __init__(
        self,
        graph_retriever: GraphRetriever,
        engine: RagEngine,
        *,
        depth: int | None = None,
    ) -> None:
        self._retriever = graph_retriever
        self._engine = engine
        self._generator = engine.generator
        self._depth = depth

    def run(self, query: str, context: AgentContext | None = None) -> AgentRun:
        org = context.organization_id if context else None
        ws = context.workspace_id if context else None
        memories = list(context.memories) if context else []
        history = list(context.history) if context else []

        steps: list[AgentStep] = []

        graph_ctx = self._retriever.retrieve(
            query, organization_id=org, workspace_id=ws, depth=self._depth
        )
        steps.append(
            AgentStep(
                thought="Traverse the knowledge graph for related entities.",
                tool="graph_traverse",
                tool_input={"query": query},
                observation=(
                    f"{len(graph_ctx.entities)} entity(ies), "
                    f"{len(graph_ctx.facts)} relationship(s)."
                ),
            )
        )

        # Supporting passages from the documents (tenant-scoped); may be empty.
        where = {"workspace_id": ws} if ws else None
        evidence = self._engine.search(query, where=where)
        steps.append(
            AgentStep(
                thought="Retrieve supporting passages for detail and citations.",
                tool="rag_search",
                tool_input={"query": query},
                observation=f"{len(evidence)} passage(s) found.",
            )
        )

        if not graph_ctx.facts and not evidence and not memories:
            return AgentRun(
                query=query,
                answer=(
                    "I don't have enough information in the knowledge graph or "
                    "documents to answer that."
                ),
                steps=steps,
            )

        context_block, citations = build_context(evidence)
        graph_block = graph_ctx.as_text() or "(no related entities found)"
        user_prompt = _context_preamble(memories, history)
        user_prompt += (
            f"Known relationships from the knowledge graph:\n{graph_block}\n\n"
            f"Sources:\n{context_block}\n\nQuestion: {query}"
        )
        answer = self._generator.generate(SYSTEM_PROMPT, user_prompt)
        steps.append(
            AgentStep(
                thought="Synthesise an answer from graph facts and evidence.",
                observation=(
                    f"Answer drafted from {len(graph_ctx.facts)} fact(s) "
                    f"and {len(citations)} source(s)."
                ),
            )
        )
        return AgentRun(
            query=query,
            answer=answer,
            steps=steps,
            citations=citations,
            metadata={
                "graph_facts": [f.as_text() for f in graph_ctx.facts],
                "entities": [e.name for e in graph_ctx.entities],
            },
        )
