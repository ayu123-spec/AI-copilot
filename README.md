# Enterprise AI Knowledge Copilot — Phase 0 (Foundations & Accounts)

This is the **v0.1 foundation**: authentication, multi-tenant user management,
workspace management, and the project infrastructure (config, logging, async DB,
Docker, tests, CI) that every later module builds on.

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
- `docker-compose` for API + Postgres
- Pytest suite (auth flows + tenant-isolation tests) and GitHub Actions CI

## Run it

```bash
# With Docker (API + Postgres)
docker-compose up --build
# API docs: http://localhost:8000/docs

# Or locally against SQLite
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

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

## Known simplifications (intentional for Phase 0)

- Email verification logs the token instead of sending mail — swap in an email
  provider when convenient.
- Tables are created on startup (`create_all`). Before Phase 1, add Alembic
  migrations so schema changes are versioned.
- `JWT_SECRET` defaults to a placeholder; set a real one via `.env` everywhere.

## Next: Phase 1

Data ingestion engine, document processing, chunking strategies, embedding
pipeline, and the Qdrant vector store. See `BUILD_PLAN.md`.
