# Enterprise AI Knowledge Copilot — Phases 0–1

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
pytest -q          # 11 tests: auth flows + multi-tenant isolation
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

## Known simplifications (intentional for Phase 0)

- Email verification logs the token instead of sending mail — swap in an email
  provider when convenient.
- Tables are created on startup (`create_all`). Before Phase 1, add Alembic
  migrations so schema changes are versioned.
- `JWT_SECRET` defaults to a placeholder; set a real one via `.env` everywhere.

## Next: Phase 2

The RAG engine: BM25 sparse retrieval alongside the existing dense search, hybrid
fusion, cross-encoder re-ranking, citation building, and a streaming chat answer
endpoint. See `BUILD_PLAN.md`.
