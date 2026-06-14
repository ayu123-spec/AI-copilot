# Enterprise AI Knowledge Copilot — Phases 0–4 (complete)

**v0.1** is the foundation (auth, multi-tenant users, workspaces, infra).
**v0.2** adds the ingestion engine: upload documents, parse + clean + chunk + embed
them, store vectors in Qdrant, and run semantic search — all tenant-scoped.

## What's implemented

**Authentication & user management**
- Register an organization + its first user (assigned `admin`)
- Password hashing (bcrypt), JWT access + refresh tokens
- Email verification flow (token logged in Phase 0; wire to email later)
- Roles: `admin` / `manager` / `employee`, enforced per endpoint
- **Multi-tenant isolation**: every query is scoped to the caller's organization

**Workspace management**
- Create workspaces, list them (org-scoped)
- Invite existing org users into a workspace with a role
- Per-workspace settings (upload limit, storage quota, agent permissions)

**Infrastructure**
- FastAPI + async SQLAlchemy 2.0 (Postgres in prod, SQLite for tests)
- `docker-compose` for API + Postgres + Qdrant
- Pytest suite (auth flows + tenant-isolation tests) and GitHub Actions CI

## What's implemented — Phase 1 (Ingestion engine, v0.2)

**Ingestion** — parsers for PDF, DOCX, PPTX, TXT, Markdown that preserve page/slide
numbers, then a cleaning pass (whitespace, page-number headers/footers).

**Chunking** — four interchangeable strategies: `fixed`, `recursive`, `semantic`
(groups sentences by embedding similarity), and `parent_child` (small chunks carry
their larger parent for context).

**Embeddings** — a pluggable `Embedder` interface with three backends:
- `local` — sentence-transformers (default `bge-small-en-v1.5`, 384-dim)
- `openai` — `text-embedding-3-small`
- `fake` — deterministic, offline, used by tests

**Vector store (Qdrant)** — collection management, metadata filters, namespace
isolation, similarity search, and delete-by-document. Runs against a Qdrant server
(`QDRANT_URL`) or, with no URL set, an embedded on-disk store — so it works locally
with no server.

**Pipeline + API** — `upload → parse → clean → chunk → embed → store`, exposed as
tenant-scoped endpoints. Search is always filtered to the caller's org + workspace.

## What's implemented — Phase 3 (Agents & orchestration, v0.4)

**Research agent** — wraps the RAG engine as a reusable `rag_search` tool, gathers
evidence (optionally across several refinement hops, de-duplicated by chunk), and
synthesises one cited answer. Tenant-scoped, and able to draw on long-term memory.

**SQL agent** — answers quantitative questions over a seeded analytics database
(`regions`, `products`, `sales`) by writing read-only SQL. Guardrails are defence in
depth: every connection runs `PRAGMA query_only = ON` (writes rejected by the driver),
*and* a `sqlparse`-based guard independently enforces a single read-only `SELECT` over
allow-listed tables, with a `LIMIT` injected. Rejected queries are revised and retried;
the generated SQL is always returned for transparency.

**Orchestrator (LangGraph)** — a compiled `StateGraph` classifies each query and routes
it to the right agent, then records which agent handled it. Routing is pluggable: a
deterministic keyword router (the default, fully offline) or an LLM router.

**Memory** — two tenant-scoped layers. *Short-term* is the recent turns of the current
conversation; *long-term* is durable `MemoryItem` records embedded into a Qdrant memory
collection for semantic recall across conversations. Both are assembled into the agent's
context for each run.

**Persistence & API** — every run is saved as an inspectable `AgentRunRecord` (chosen
agent, answer, citations, full step trace). Endpoints run the orchestrator (or a forced
agent), list/fetch run traces, and add/list/recall memories. Runs optionally persist to
the chat history as a conversation.

**Routing evaluation** — `app/evaluation/agent_eval.py` measures routing accuracy on a
small labelled query set.

## What's implemented — Phase 4 (Knowledge graph, GraphRAG & Multimodal, v0.5)

**Knowledge graph** — a tenant-scoped property graph of entities (Person, Company,
Project, Department) and relationships (`WORKS_FOR`, `MANAGES`, `REPORTS_TO`, `PART_OF`,
`WORKS_ON`) extracted from documents. The `GraphStore` interface has two backends: an
in-process store (default, offline, used by tests and local dev) and a **Neo4j** store
for production (`GRAPH_BACKEND=neo4j`, driver lazy-imported). Entity ids are deterministic
so the same entity merges across documents.

**Entity extraction** — pluggable behind one interface: a deterministic, offline
`RuleBasedEntityExtractor` (proper-noun + relationship-verb patterns with suffix/keyword
typing) by default, and an opt-in `LLMEntityExtractor` (`GRAPH_ENTITY_EXTRACTOR=llm`).

**GraphRAG** — `GraphRetriever` spots the entities a query mentions, traverses their
relationships up to `GRAPH_MAX_HOPS` hops, and returns the facts. A new **graph agent**
joins the orchestrator (relationship/multi-hop questions route to it) and fuses those
graph facts with vector-retrieved passages — answering multi-hop questions that pure
vector search cannot, while still citing documents.

**Multimodal RAG** — images (charts, diagrams, scanned pages) become first-class,
citable evidence. On upload, an image is passed through a pluggable `ImageDescriber`
that produces a text description; that text is chunked, embedded, and stored like any
other content, tagged with `modality="image"`. The describer has two backends: a
deterministic, offline `FakeImageDescriber` (default, used by tests and local dev) and
an opt-in vision-LLM `LLMImageDescriber` (`IMAGE_DESCRIBER_BACKEND=anthropic`,
SDK lazy-imported). The result: "explain this chart" works, and search results report
whether a hit came from text or an image.

This completes Phase 4 → **v0.5**.

## Run it

```bash
# With Docker (API + Postgres + Qdrant)
docker-compose up --build
# API docs: http://localhost:8000/docs

# Or locally against SQLite + embedded Qdrant
pip install -r requirements-dev.txt          # base + test deps
pip install -r requirements-ml.txt           # only for local embeddings (pulls torch)
uvicorn app.main:app --reload
```

To try ingestion locally without downloading a model, set `EMBEDDING_BACKEND=fake`
(or `openai` with `OPENAI_API_KEY`). The default `local` backend downloads
`bge-small-en-v1.5` (~130 MB) on first use.

## Test it

```bash
pip install -r requirements-dev.txt
pytest -q          # 146 tests: auth, ingestion, RAG, agents, memory, graph, multimodal + tenant isolation
```

## API surface (prefix `/api/v1`)

| Method | Path                              | Role          | Purpose                       |
|--------|-----------------------------------|---------------|-------------------------------|
| POST   | `/auth/register`                  | public        | Create org + admin user       |
| POST   | `/auth/login`                     | public        | Get access + refresh tokens   |
| POST   | `/auth/refresh`                   | public        | Exchange refresh for access   |
| POST   | `/auth/verify`                    | public        | Verify email via token        |
| GET    | `/users/me`                       | any           | Current user                  |
| GET    | `/users`                          | admin/manager | List org users                |
| POST   | `/workspaces`                     | admin/manager | Create workspace              |
| GET    | `/workspaces`                     | any           | List org workspaces           |
| POST   | `/workspaces/{id}/invite`         | admin/manager | Add org user to workspace     |
| PATCH  | `/workspaces/{id}/settings`       | admin         | Update workspace settings     |
| POST   | `/workspaces/{id}/documents`      | any           | Upload + ingest a document    |
| GET    | `/workspaces/{id}/documents`      | any           | List documents in a workspace |
| POST   | `/workspaces/{id}/search`         | any           | Semantic search (org-scoped)  |
| DELETE | `/documents/{id}`                 | admin/manager | Delete a document + vectors   |
| POST   | `/workspaces/{id}/chat`           | any           | Ask a grounded, cited question|
| POST   | `/workspaces/{id}/chat/stream`    | any           | Streamed (SSE) answer         |
| GET    | `/workspaces/{id}/conversations`  | any           | List chat conversations       |
| GET    | `/conversations/{id}/messages`    | any           | Conversation message history  |
| POST   | `/messages/{id}/feedback`         | any           | 👍/👎 on an assistant message  |
| POST   | `/workspaces/{id}/agents/run`     | any           | Run orchestrator / forced agent|
| GET    | `/workspaces/{id}/agents/runs`    | any           | List persisted run traces     |
| GET    | `/agents/runs/{id}`               | any           | Fetch one run trace           |
| POST   | `/workspaces/{id}/memories`       | any           | Add a long-term memory        |
| GET    | `/workspaces/{id}/memories`       | any           | List long-term memories       |
| POST   | `/workspaces/{id}/memories/recall`| any           | Semantic memory recall        |
| POST   | `/workspaces/{id}/graph/build`    | any           | Build the KG from documents   |
| GET    | `/workspaces/{id}/graph/entities` | any           | Search graph entities         |
| GET    | `/workspaces/{id}/graph/entities/{name}/neighbors` | any | Traverse an entity's relations |
| POST   | `/workspaces/{id}/graph/query`    | any           | GraphRAG retrieval (facts)    |

## Known simplifications (intentional for Phase 0)

- Email verification logs the token instead of sending mail — swap in an email
  provider when convenient.
- Tables are created on startup (`create_all`) for convenience, but **Alembic
  migrations are included** — run `alembic upgrade head` for versioned schema changes.
- `JWT_SECRET` defaults to a placeholder; set a real one via `.env` everywhere.

## Evaluation

Retrieval quality is measured with a small, reproducible harness:

```
python -m app.evaluation.run
```

It reports hit rate, MRR, and precision@k over a fixed set of questions. Run it with
`EMBEDDING_BACKEND=local` (after `pip install -r requirements-ml.txt`) for numbers that
reflect real embedding quality, and expand the cases in `app/evaluation/run.py` to match
your own documents. For answer-level metrics (faithfulness, answer relevance), RAGAS can
be layered on top with an LLM judge.

| Metric        | Score |
|---------------|-------|
| Hit rate      | TBD   |
| MRR           | TBD   |
| Precision@k   | TBD   |

## Running the agents

The agents and routing run fully offline with `EMBEDDING_BACKEND=fake` and the default
`fake` LLM backend (the SQL agent will decline rather than invent SQL). For real answers
and LLM-driven routing, set `LLM_BACKEND=anthropic`, provide `ANTHROPIC_API_KEY`, and
`pip install anthropic`; for real semantic memory recall, use `EMBEDDING_BACKEND=local`.

The knowledge graph defaults to an in-process store (no server). For a real graph, set
`GRAPH_BACKEND=neo4j` with `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (the `neo4j`
driver is already in `requirements.txt`), and optionally `GRAPH_ENTITY_EXTRACTOR=llm`.

## Evaluation

The `app/evaluation/` package scores both retrieval and answer quality on a fixed,
version-controlled regression set (`dataset.py`), so results are comparable across changes.

- **Retrieval** — precision@k, recall@k (hit rate), MRR (`metrics.py`, `harness.py`).
- **Answer quality** — faithfulness, hallucination rate, answer relevance, and citation
  accuracy (`answer_metrics.py`): deterministic, offline heuristics, with an opt-in
  `LLMJudge` for LLM-graded faithfulness (RAGAS/DeepEval-style).
- **Routing** — orchestrator routing accuracy (`agent_eval.py`).

Run the end-to-end answer report:

```bash
python -m app.evaluation.run_full
```

With the default `fake` LLM the numbers are illustrative; set `LLM_BACKEND=anthropic`
(+ `ANTHROPIC_API_KEY`) for meaningful, publishable numbers. The metric functions are
covered by tests so they stay honest on every change.

## Next: Phase 5

Phase 4 is complete (**v0.5**). Phase 5 (**v0.6**) adds trust & observability:
an evaluation framework, guardrails, an analytics dashboard, and notifications.
See `BUILD_PLAN.md`.
