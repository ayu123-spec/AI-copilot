# Build Plan — Enterprise AI Knowledge Copilot (Full Scope)

**Total effort:** ~21 weeks of focused work (≈ 5 months full-time, ≈ 10–12 months part-time).
**Strategy:** ship each phase as a tagged, deployable GitHub release. A green, working
release at every stage beats a perpetual work-in-progress.

> Estimates assume one developer comfortable with Python/FastAPI. Multiply by ~2–2.5
> if you are learning the stack while building, or working evenings/weekends only.

---

## Phase 0 — Foundations & Accounts (Weeks 1–2) → release **v0.1**

**Module 1 — Authentication & User Management** *(~5 days)*
- Email signup, password hashing (bcrypt/argon2), email verification
- Login with JWT access + refresh tokens
- Roles: Admin / Manager / Employee
- Multi-tenant architecture: isolated data per organization
- *Done:* two orgs cannot see each other's data; verified by isolation tests.

**Module 2 — Workspace Management** *(~3 days)*
- Create workspaces (e.g. Finance, Legal)
- Invite users by email, assign roles
- Workspace settings: upload limits, storage usage, agent permissions
- *Done:* a user can create a workspace, invite a teammate, and scope access.

**Project infra** *(~2 days)*
- Repo, `docker-compose` (API + Postgres), FastAPI skeleton, config, structured logging
- GitHub Actions CI scaffold (lint + tests on every push)

---

## Phase 1 — Ingestion & Processing (Weeks 3–5) → release **v0.2**

**Module 3 — Data Ingestion Engine** *(~8 days)*
- File parsers: PDF, DOCX, TXT, Markdown, PPT/PPTX, CSV/XLSX
- Website ingestion: single URL + recursive crawler
- Connectors: REST APIs, PostgreSQL, MySQL
- Extract text, tables, metadata, images; persist chunk schema
  (`document_name`, `page_number`, `chunk_id`, `workspace_id`)
- *Done:* every supported source type ingests into a uniform document record.

**Module 4 — Document Processing Pipeline** *(~5 days)*
- Cleaning: remove extra whitespace, headers, footers, watermarks
- Metadata extraction: author, created date, source
- Chunking strategies: fixed (500 tokens), recursive, semantic
  (sentence-transformers), parent-child, hierarchical
- *Done:* a document flows clean → chunked under any chosen strategy.

**Module 5 — Embedding Pipeline** *(~3 days)*
- Pluggable backends: OpenAI / BGE-large / E5-large
- Batched embedding, store chunk + embedding + metadata
- *Done:* chunks embedded and persisted with full metadata.

**Module 6 — Vector Database (Qdrant)** *(~4 days)*
- Similarity search, metadata filters, hybrid-ready collections
- Namespace support, collection management
- *Done:* filtered vector search across namespaces works.

---

## Phase 2 — Core RAG & Chat (Weeks 6–8) → release **v0.3**

**Module 7 — RAG Engine** *(~7 days)*
- Dense (vector) + sparse (BM25) retrieval, hybrid fusion (RRF)
- Cross-encoder re-ranking, top-K context building
- Citation generation (source + page)
- *Done:* answers are grounded and cite exact pages.

**Module 8 — AI Chat Interface** *(~7 days)*
- ChatGPT-style UI, streaming responses, Markdown + citations
- Chat history, follow-up questions, regenerate, 👍/👎 feedback
- *Done:* a polished, streaming, cited chat experience.

**Module 18 — Caching (Redis)** *(~3 days, pulled forward)*
- Cache embeddings, retrieval results, LLM responses; invalidation
- *Done:* repeat queries are visibly faster. (Built early so later phases benefit.)

---

## Phase 3 — Agents & Orchestration (Weeks 9–11) → release **v0.4**

**Module 9 — Agent System** *(~9 days)*
- Research agent (search + retrieve), SQL agent (query DB)
- Report agent (weekly/monthly summaries), Web Search agent
- Planning agent (decompose complex tasks)
- *Done:* each agent works in isolation and via the planner.

**Module 10 — LangGraph Workflow** *(~4 days)*
- Graph: Query → Planner → Retriever → Tool selection → Agent execution
  → Validation (groundedness) → Final response, with retries
- *Done:* the graph routes a query through the right agents and validates output.

**Module 11 — Memory System** *(~4 days)*
- Short-term conversation memory
- Long-term memory: user preferences, past interactions, workspace knowledge
- Semantic memory search
- *Done:* the system recalls relevant past context across sessions.

---

## Phase 4 — Knowledge Graph & Advanced Retrieval (Weeks 12–15) → release **v0.5** ✅ COMPLETE

**Module 12 — Knowledge Graph (Neo4j)** *(~6 days)* ✅
- Entity extraction: Person, Company, Project, Department
- Relationships: WORKS_FOR, MANAGES, REPORTS_TO; Cypher queries
- *Done:* documents populate a queryable graph (in-process + Neo4j backends).

**Module 13 — GraphRAG** *(~6 days)* ✅
- Fuse knowledge-graph traversal with vector retrieval for multi-hop questions
- *Done:* answers questions pure vector search cannot (multi-hop reasoning).

**Module 14 — Multimodal RAG** *(~6 days)* ✅
- Ingest and reason over images, charts, tables, scanned pages
- Pluggable ImageDescriber (offline fake default + lazy vision-LLM backend);
  image text indexed with `modality="image"`
- *Done:* a chart/image query returns a grounded explanation; 146 tests pass.

---

## Phase 5 — Trust, Quality & Observability (Weeks 16–18) → release **v0.6**

**Module 15 — Evaluation Framework** *(~5 days)*
- Metrics: faithfulness, context precision/recall, hallucination rate, latency, cost
- Frameworks: RAGAS + DeepEval; fixed regression test set
- *Done:* published numbers in the README, re-runnable on every change.

**Module 16 — Guardrails** *(~5 days)*
- Protect against prompt injection, data leakage, hallucination, toxic output
- Frameworks: Guardrails AI / NeMo Guardrails, wired into the graph
- *Done:* injection and PII-leak attempts are blocked, proven by tests.

**Module 17 — Analytics Dashboard** *(~5 days)*
- Track queries, active users, retrieval accuracy, cost, agent usage, tokens
- Charts: daily queries, popular documents, response times
- *Done:* a live dashboard reflects real usage.

**Module 19 — Notifications** *(~3 days)*
- Email, Slack, Teams integrations
- *Done:* configurable alerts fire to the chosen channel.

---

## Phase 6 — Production Hardening (Weeks 19–21) → release **v1.0**

**Module 20 — Deployment** *(~8 days)*
- Docker images, Nginx reverse proxy
- AWS deployment, GitHub Actions CI/CD, Terraform infrastructure-as-code
- *Done:* one-command/pipeline deploy to a public URL.

**Hardening & launch** *(~5 days)*
- Security review, load testing, full docs in `/docs`, 60-second demo GIF
- *Done:* v1.0 is live, documented, demoable.

---

## If you fall behind

Protect, in this order of importance: (1) a working end-to-end demo, (2) citations,
(3) published evaluation numbers, (4) README + demo polish. If a phase overruns, push
the most exotic module (multimodal RAG, then GraphRAG, then notifications) into a
"Future work" section rather than shipping it broken. A finished, smaller release
always beats a sprawling broken one.
