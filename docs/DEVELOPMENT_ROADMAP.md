# DIVU AI — Development Roadmap

**Founder & Creator:** DIVYESH BAMBHANIYA · *Beyond Conversations. Towards Intelligence.*

Legend: ✅ complete · 🟡 partial · ○ not started

| Phase | Name | Status | Key deliverables |
|---|---|---|---|
| 0 | Architecture & analysis | ✅ | `SYSTEM_ARCHITECTURE.md`, `PHASE0_ANALYSIS.md` |
| 1 | Foundation & architecture | ✅ | Config, logging, error envelope, DB + Alembic baseline, authN/RBAC, audit, rate limit, injection screening, health probes, CI |
| 2 | Frontend & backend | 🟡 | Next.js app + brand + auth + live system status (chat workspace lands in Phase 3) |
| 2b | Website + installable PWA | ✅ | Marketing site, workspace at `/app`, install page, PWA manifest, service worker, icon set, offline page, downloadable app package |
| 3 | AI chat & model router | ○ | Provider adapters, capability matrix, SSE streaming, retries/fallback/timeouts, token & cost tracking |
| 4 | Memory & RAG | ○ | 5 memory types + user controls; ingest → chunk → embed → index → retrieve → rerank → cite |
| 5 | Agent framework | ○ | Agent CRUD/runner, 8 built-in agents, permissions, execution limits |
| 6 | Tool integration | ○ | Tool registry, schema validation, sandboxed execution, per-agent permissions |
| 7 | Developer Studio & add-ons | ○ | Add-on SDK + registry + full lifecycle + versioning/rollback + AI-assisted scaffolding (never auto-trusted) |
| 8 | Multimodal | ○ | Images, audio/speech, PDFs & documents, video metadata; unsupported modes reported honestly |
| 9 | Multi-agent collaboration | ○ | Manager delegation, shared context, aggregation, independent review, anti-recursion limits |
| 10 | Evaluation, security & deployment | ○ | Eval harness with recorded metrics, hardening, Docker/k8s deploy, backup & recovery |

## Phase 1 — Foundation and architecture ✅

**Architecture:** config → logging → errors → db → security → api. Everything is a small,
independently testable module; routers stay thin; repositories own persistence; secrets are
encrypted and redacted.

**Implemented**
- `backend/app/core`: typed settings (`DIVU_*`), structured logging with secret redaction,
  strict error envelope with `request_id`, UTC/id helpers.
- `backend/app/db`: SQLAlchemy 2.0 async engine (Postgres+asyncpg **or** SQLite+aiosqlite),
  declarative base + mixins, models for users/roles/refresh tokens/API keys/provider
  credentials/audit logs/usage events, Alembic baseline migration (reversible).
- `backend/app/security`: PBKDF2 password hashing, JWT access/refresh with rotation and reuse
  detection, Fernet encryption for secrets at rest (HKDF-derived key), RBAC guards, sliding-window
  rate limiter (Redis or in-memory), audit service, prompt-injection screening.
- `backend/app/api`: `/health/live`, `/health/ready`, `/health/version`, `/api/v1/auth/*`
  (register, login, refresh, logout, me, change password), `/api/v1/users/*` (admin),
  `/api/v1/audit/*` (admin), `/api/v1/system/info`.
- Tests: unit + integration (SQLite), ruff, `Makefile`, `.env.example`, `docker-compose.yml`,
  GitHub Actions CI, phase report in `docs/phases/PHASE_1_FOUNDATION.md`.

**Incomplete / deferred**
- 🟡 Frontend: only the app shell + status/auth screens exist; the chat workspace is Phase 3.
- ○ Password reset via email, SSO/OIDC, MFA: not implemented.
- ○ Redis-backed rate limiting is implemented but unverified here (no Redis in this sandbox);
  the in-memory backend is what the tests exercise.
- ○ Prometheus `/metrics` wiring ships from Phase 3 onward (package already pinned).

## Phase 2 — Frontend and backend (in progress)

- Next.js 15 App Router, TypeScript, Tailwind; brand header (DIVU AI / DIVYESH BAMBHANIYA,
  Founder & Creator), responsive shell (mobile + desktop).
- Typed API client with token storage, refresh handling, error envelope surfacing.
- Live backend status panel, sign in / register, prompt-injection screening playground.
- Remaining: chat workspace, file upload, agent/model selectors → Phase 3+.

## Phase 2b — Website and installable app ✅

- **Website** (`/`): hero, live build strip (server-rendered from the API, revalidated every 30s),
  platform capabilities, ten-phase roadmap, security section, install CTA.
- **Workspace** (`/app`): the operational dashboard, PWA `start_url`.
- **Install page** (`/download`): install button, package download, contents and quick start,
  plus honest notes about Android APK generation and iOS Safari.
- **PWA**: `manifest.webmanifest` (name, icons incl. maskable, standalone display, shortcuts),
  service worker (precached shell, cache-first hashed assets, network-only `/api`, offline
  fallback page), generated icon set (192/256/384/512/maskable/apple-touch/favicon/og-cover).
- **Offline behaviour**: the installed app always opens; live features reconnect when the network
  returns. API responses are deliberately never cached.
- **Downloadable package**: `make package` builds `divu-ai-app.zip` (frontend + backend + docs +
  `start.sh` / `start.bat` + install README).
- Scripts: `scripts/generate_icons.py`, `scripts/build_download_package.py`.

## Phase 3 — AI chat and model router (planned)
- Provider adapters: OpenAI-compatible, Anthropic, Google, plus a deterministic **mock** provider
  so the platform is fully runnable with no API key.
- Capability matrix (streaming, tools, vision, JSON mode, context window), cost table, health
  tracking, policy-based routing (capability → cost → latency → availability), timeouts/retries
  with jitter, streaming via SSE, per-request token and cost accounting.

## Phase 4 — Memory and RAG (planned)
- Session / conversation / long-term / episodic / knowledge memory; relevance-ranked retrieval;
  inspect, edit, export, delete; audit on every write.
- RAG: upload → extraction → cleaning → chunking → embedding → pgvector index → hybrid retrieval
  → reranking → generation → citation. No invented citations; retrieved vs. interpreted text is
  visually distinguished.

## Phase 5 — Agent framework (planned)
- Agent schema (id, name, description, instructions, model config, tools, knowledge, permissions,
  limits, memory config, eval tests, status), runner with step/token/time budgets.
- Built-ins: General Assistant, Research, Coding, Mathematics, Data Analysis, Document Analysis,
  Planning, Quality Review.

## Phase 6 — Tool integration (planned)
- Tool registry with JSON-schema args, permission scopes, sandboxed subprocess execution with
  rlimits/no-network/timeouts, structured results, failure isolation.

## Phase 7 — Developer Studio and dynamic add-ons (planned)
- Studio: new feature / agent / model / API / tool / knowledge / workflow / add-on management,
  testing, debugging, enable-disable, versioning, rollback.
- Add-on SDK + registry: manifest, id, version, entrypoint, dependencies, permissions, limits,
  test results, install status; lifecycle
  `create → validate → scan → sandbox test → approve → install → register → activate`.
- AI-assisted add-on generation is **advisory**: output is scanned, sandboxed, and requires
  explicit user approval. Core app is protected by a supervisor that disables failing extensions.

## Phase 8 — Multimodal (planned)
- Text, image (vision input + generation), audio (STT/TTS), PDF/document understanding, video
  (metadata/frames/transcript) behind provider-independent interfaces; unsupported capabilities
  return an explicit "unsupported" result instead of pretending.

## Phase 9 — Multi-agent collaboration (planned)
- Manager agent with delegation, structured messaging, status tracking, shared context,
  aggregation, independent reviewer, failure handling, global depth/step/time limits to prevent
  uncontrolled recursion.

## Phase 10 — Evaluation, security and deployment (planned)
- Eval harness: unit, integration, model quality, RAG retrieval quality, factual & citation
  accuracy, agent task completion, permission enforcement, security, performance, recovery —
  results recorded and published in the admin dashboard.
- Hardening pass, `pip-audit`/`npm audit`, penetration test checklist, Docker Compose + k8s
  manifests, backup/restore automation and drill.
