# DIVU AI — Phase 0 Analysis (pre-implementation)

This document satisfies specification §20 ("First Execution Instruction"): folder structure,
dependency and compatibility analysis, milestone plan, hardware requirements, deployment
options, security risk register, and acceptance tests.

---

## 1. Folder structure

```
DIVU-AGI/
├── README.md                      Product overview, quickstart, brand
├── LICENSE
├── .gitignore                     (extended: Python, Node, env, data, artifacts)
├── .env.example                   Every config variable, no secrets
├── docker-compose.yml             Postgres+pgvector, Redis, MinIO, backend, frontend
├── Makefile                       setup / dev / test / lint / migrate / seed
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md     Topology, module map, contracts
│   ├── PHASE0_ANALYSIS.md         This file
│   ├── DATABASE_SCHEMA.md         Table-by-table reference
│   ├── API_DOCUMENTATION.md       REST + SSE contracts
│   ├── AGENT_DEVELOPMENT_GUIDE.md How to build an agent
│   ├── ADDON_SDK_GUIDE.md         Add-on SDK, manifest, lifecycle
│   ├── SECURITY_GUIDE.md          Threat model, controls, operations
│   ├── DEPLOYMENT_GUIDE.md        Local, Docker, cloud, k8s
│   ├── DEVELOPMENT_ROADMAP.md     10 phases, milestones, status
│   └── phases/PHASE_1_FOUNDATION.md   Per-phase completion report
├── backend/
│   ├── requirements.txt, requirements-dev.txt, pyproject.toml, alembic.ini
│   ├── migrations/                Alembic (async), one revision per phase
│   ├── app/                       (see SYSTEM_ARCHITECTURE §3)
│   └── tests/                     unit / integration / security / eval
├── frontend/
│   ├── package.json, next.config.ts, tailwind.config.ts, tsconfig.json
│   └── src/{app,components,lib,hooks,styles}
├── addons/                        First-party example add-ons
├── scripts/                       dev/bootstrap helpers
└── .github/workflows/ci.yml       lint + test + build on every push
```

Separation rule: **frontend never talks to a database or a provider**; **backend never renders
UI**; **add-ons never import backend internals** (they use the SDK surface only).

---

## 2. Dependencies and compatibility analysis

### Backend (pinned, verified installable on Python 3.11)

| Package | Version | Role | Compatibility risk / mitigation |
|---|---|---|---|
| Python | 3.11 | Runtime | 3.12/3.13 also supported; CI matrix 3.11 + 3.12 |
| FastAPI | 0.115.6 | HTTP framework | Pydantic v2 native; keep <0.116 in lockstep with Starlette |
| Starlette | (pinned by FastAPI) | ASGI | — |
| Uvicorn | 0.34.0 (`standard`) | ASGI server | `httptools`/`uvloop` wheels available |
| Pydantic | 2.10.4 | Validation | v2 API only; no v1 shims used |
| pydantic-settings | 2.7.0 | Config | Env prefix `DIVU_` |
| SQLAlchemy | 2.0.36 | ORM | 2.0-style `Mapped[]` only; async engine |
| Alembic | 1.14.0 | Migrations | async migration template |
| asyncpg | 0.30.0 | Postgres driver | Prod only; not imported when URL is SQLite |
| aiosqlite | 0.20.0 | SQLite driver | Dev/CI only (keeps tests runnable with zero services) |
| python-jose | 3.3.0 | JWT | HS256 now, RS256-ready interface |
| cryptography | 44.x | Fernet encryption, key derivation | Used for secret-at-rest + HKDF |
| httpx | 0.28.x | Provider HTTP client | Async, HTTP/2-capable, streaming |
| redis | 5.2.x | Cache/rate limit/queue | Optional: `memory` backend fallback |
| structlog | 24.4.x | Structured logging | JSON in prod, console in dev |
| prometheus-fastapi-instrumentator | 7.0.0 | `/metrics` | Optional import |
| pytest / pytest-asyncio / pytest-cov | 8.3.4 / 0.25.0 / 6.0.0 | Tests | Async tests in strict mode |
| ruff | 0.8.4 | Lint/format | Replaces black+isort+flake8 |

Planned in later phases (added only when the phase lands, so the lockfile never references
unused packages): `pgvector`, `tiktoken`, `numpy`, `pypdf`, `python-docx`, `openai`, `anthropic`
(SDKs used only inside their provider adapter), `sentence-transformers`/`onnxruntime` (optional
local embeddings), `celery`/`arq` (if queue needs outgrow Redis streams).

**Known risks**

1. *Provider SDK churn* → mitigated by adapters behind `LLMProvider`; adapters are the only files
   that import a vendor SDK, and each declares a capability matrix.
2. *Pydantic v2 / SQLAlchemy 2.0 typing* → strict `Mapped[]` usage, `mypy` optional, ruff rules
   enforce no untyped public functions.
3. *Async SQLite* → single writer; dev only. Production is Postgres; the repository layer never
   uses SQLite-specific SQL.
4. *pgvector availability* → RAG runs with an in-process vector store fallback; pgvector is used
   when the extension is present (detected at startup, surfaced in `/health/ready`).
5. *Node/Next major upgrades* → frontend pinned to the Next 15 LTS backport line (15.5.x) with
   React 19; upgrades are a dedicated chore, never bundled with feature work.

### Frontend (pinned)

| Package | Version | Role |
|---|---|---|
| Next.js | 15.5.x (App Router) | Framework, dev proxy for `/api` |
| React / React DOM | 19.2.x | UI |
| TypeScript | 5.x | Types |
| Tailwind CSS | 3.4.x | Styling |
| ESLint | 9.x (`eslint-config-next`) | Lint |

### Infrastructure

Docker Compose: `pgvector/pgvector:pg16`, `redis:7-alpine`, `minio/minio` (S3-compatible object
storage), `python:3.11-slim` (backend), `node:22-alpine` (frontend build/serve).

---

## 3. Development milestone plan

| Phase | Milestone | Exit criteria (all must hold) |
|---|---|---|
| 0 | Architecture & analysis | This document + SYSTEM_ARCHITECTURE + ROADMAP approved |
| 1 | **Foundation** | Config, logging, error envelope, DB layer + Alembic baseline, authN/RBAC, audit, rate limit, health probes, CI green |
| 2 | **Frontend & backend** | Next.js shell with brand, auth flows, live system status; API client + typed contracts |
| 3 | **AI chat & router** | Real multi-provider chat (SSE streaming), capability-aware routing, retries/fallback/timeouts, token+cost tracking |
| 4 | **Memory & RAG** | 5 memory types with user controls; full RAG pipeline with citations and no invented sources |
| 5 | **Agent framework** | Agent CRUD + runner + 8 built-in agents + permissions + limits |
| 6 | **Tool integration** | Tool registry, schema validation, sandboxed execution, per-agent permissions |
| 7 | **Developer Studio & add-ons** | Add-on SDK + registry + lifecycle (create→validate→scan→sandbox→approve→install→register→activate) + versioning/rollback |
| 8 | **Multimodal** | Images, audio/STT/TTS, PDFs & documents, video metadata; unsupported modes explicitly reported |
| 9 | **Multi-agent** | Manager delegation, shared context, result aggregation, independent review, failure handling, anti-recursion limits |
| 10 | **Evaluation, security, deployment** | Eval harness with recorded metrics, security hardening pass, Docker/k8s deploy, backup & recovery drills |

Each phase ships with: code → tests → fixes → docs → integration verification → a phase report
listing **completed** and **incomplete** items.

---

## 4. Minimum hardware requirements

| Tier | vCPU | RAM | Disk | Notes |
|---|---|---|---|---|
| **Local dev / CI** (SQLite, mock provider) | 2 | 4 GB | 10 GB | Runs the full test suite and UI with zero external services |
| **Single-node demo** (Docker Compose: Postgres+pgvector, Redis, MinIO, API-hosted LLMs) | 4 | 8 GB | 40 GB | ~50 concurrent chats |
| **Small production** (API-hosted LLMs) | 8 | 16 GB | 100 GB SSD | Postgres+pgvector+Redis on separate volumes |
| **Production with local models** (e.g. 7–14B open weights + embeddings) | 8–16 | 32–64 GB | 200 GB+ SSD | Add GPU: 24 GB VRAM (L4/A10G) for 7B-class, 48–80 GB for 70B-class |
| **Vector scale guidance** | — | ~2 GB RAM per 1M 1536-dim vectors (HNSW) | ~6 GB disk per 1M vectors incl. index | Use pgvector HNSW; partition large corpora |

Object storage grows with uploads; embeddings dominate vector disk usage.

---

## 5. Deployment options

| Option | When | How | Status |
|---|---|---|---|
| **Local dev (no services)** | Contributors | `make dev` → SQLite + memory cache + mock/local provider | ✅ Available Phase 1 |
| **Docker Compose** | Demos, small teams | `docker compose up` → API + web + Postgres/pgvector + Redis + MinIO | 🟡 Compose file lands Phase 1; full stack usable from Phase 3 |
| **Single VM (systemd + Nginx/Caddy)** | Cost-sensitive prod | Uvicorn workers behind reverse proxy with TLS, Postgres managed | ⚪ Documented Phase 10 |
| **Containers on managed platform** (Render/Fly/Railway/Azure Container Apps/Cloud Run) | Teams without k8s | Two images (api, web) + managed Postgres/Redis/S3 | ⚪ Documented Phase 10 |
| **Kubernetes** | Scale, multi-tenant | Helm-style manifests, HPA on `/metrics`, secrets via CSI/external secrets | ⚪ Documented Phase 10 |
| **Air-gapped / on-prem** | Regulated users | Local model server + local Postgres/MinIO; zero egress mode flag | ⚪ Phase 10 |

Every deployment shares: env-based config, Alembic migrations on startup (guarded), health
probes (`/health/live`, `/health/ready`), structured logs to stdout, `/metrics` for Prometheus,
and **daily encrypted backups** with a tested restore.

---

## 6. Security risk register

| ID | Risk | Control | Phase |
|---|---|---|---|
| S1 | Credential leakage (provider keys, JWT secret) | Keys only in env/secret manager; Fernet encryption at rest; log redaction filter; secret scanner in CI; frontend never receives secrets | 1 |
| S2 | Broken access control | JWT with `typ`/`exp`/`jti`, RBAC guards on every router, object-level ownership checks in repositories, admin actions audited | 1 |
| S3 | Brute force / credential stuffing | Progressive rate limits, account lockout window, refresh-token rotation + reuse detection | 1 |
| S4 | Prompt injection (direct & indirect via documents/tools/web) | Injection screening on all untrusted text, trust boundary markers, tool-call allowlists, retrieval content quarantined as data-not-instructions, citation enforcement | 1 (basic) → 4/6 (full) |
| S5 | Malicious/unsafe extension code | Manifest validation, static scan (forbidden imports/patterns), sandbox test run, **explicit human approval**, resource limits, kill switch, rollback | 7 |
| S6 | Sandbox escape / RCE via tools | Subprocess isolation, no network by default, rlimits (CPU/memory/files), timeout, non-root user, seccomp where available | 6–7 |
| S7 | Data exfiltration through model/tool calls | Egress allowlist per tool, output scanning for secrets/PII, per-agent permission scopes | 6 |
| S8 | Cost/DoS abuse | Per-user and per-key quotas, token budgets, concurrency caps, circuit breakers | 3 |
| S9 | Injection into SQL/NoSQL | Parameterized queries only (SQLAlchemy), strict Pydantic validation, length limits | 1 |
| S10 | Unvalidated uploads (malware, zip bombs, SVG XSS) | MIME/extension allowlist, size caps, magic-byte check, content extracted in sandbox, stored outside webroot with random keys | 4 |
| S11 | Supply-chain compromise | Pinned dependencies, hash-pinned requirements where feasible, `pip-audit`/`npm audit` in CI, minimal base images | 1 |
| S12 | PII over-retention | Retention policies, user-facing memory view/edit/export/delete, audit trail for deletions | 4 |
| S13 | Insecure defaults in production | `app_env=production` requires strong secret, TLS-only cookies, CORS allowlist, no debug errors, startup self-check | 1 |
| S14 | Log/telemetry leakage | Redaction processor, no prompt bodies at INFO level, prompt content logging behind an explicit opt-in flag | 1 |

---

## 7. Acceptance tests

### 7.1 Global (must pass at every phase)

1. `make test` is green (unit + integration) and coverage thresholds hold (`--cov-fail-under`).
2. `make lint` is clean (ruff + eslint + `tsc --noEmit`).
3. Fresh clone → `.env.example` → `make dev` boots API and web with **no external services**.
4. `/health/live` returns 200; `/health/ready` reports dependency status honestly.
5. No secret appears in logs, responses, or the frontend bundle (`grep` gate in CI).

### 7.2 Phase 1 acceptance (this phase)

| # | Test | Expected |
|---|---|---|
| A1 | Register → login → `/auth/me` | 201 → 200 → identity matches; password never returned |
| A2 | Login with wrong password | 401 `invalid_credentials`; failure written to `audit_logs` |
| A3 | Access admin route as normal user | 403 `permission_denied` |
| A4 | Expired/altered JWT | 401 `token_invalid` |
| A5 | Refresh token rotation & reuse | Rotation issues a new pair; reuse revokes the family |
| A6 | Rate limit burst | 429 with `Retry-After` after the configured burst |
| A7 | Malformed request body | 422 with a structured error envelope and `request_id` |
| A8 | Secret encryption | Provider credential round-trips encrypted; DB column never plaintext |
| A9 | Log redaction | Known secret value never appears in emitted log lines |
| A10 | Injection screening | Known injection corpus flagged; benign corpus not flagged (precision/recall gate) |
| A11 | Migration round-trip | `alembic upgrade head` then `downgrade base` on a clean DB |
| A12 | Seed + health | Seeded admin can log in; `/health/ready` returns 200 with SQLite |

### 7.3 End-state acceptance (tracked through Phase 10)

* Chat works against at least two providers with streaming, and falls back on provider failure.
* Routing picks a model that supports the requested capability (e.g. vision) or reports unsupported.
* Memory: store → retrieve → edit → export → delete, all user-visible and audited.
* RAG: ingest PDF/TXT → ask → answer cites only retrieved chunks; zero fabricated citations (measured).
* Agents: all 8 built-ins complete their designed tasks in the eval set.
* Multi-agent: manager completes a delegated 3-agent task within step/time limits; recursion guard triggers on a crafted loop.
* Add-ons: sample add-on passes the full lifecycle; a malicious add-on is rejected by the scanner.
* Admin dashboard reflects real usage/cost numbers from `usage_events`.
* Backup → restore drill restores a seeded database.

---

## 8. Decision log

| Decision | Rationale |
|---|---|
| Async SQLAlchemy + asyncpg/aiosqlite | Uniform async API; SQLite keeps CI service-free |
| PBKDF2-HMAC-SHA256 (600k, per-user salt) over bcrypt | No C dependency, portable, OWASP-compliant parameter choice, fast tests |
| HS256 JWT now, RS256-ready abstraction | Simplicity for single-service deploy; interface supports rotation to asymmetric keys |
| SSE (not WebSockets) for token streaming | Simpler, proxy-friendly, one-way is all that's needed |
| Next 15 LTS line, not bleeding-edge 16 | Stability of App Router APIs during a 10-phase build |
| Provider calls via `httpx` in adapters | Avoids vendor SDK lock-in and version churn in the service layer |
