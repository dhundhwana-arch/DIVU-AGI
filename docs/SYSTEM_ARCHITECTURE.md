# DIVU AI — System Architecture

**Product:** DIVU AI
**Founder & Creator:** DIVYESH BAMBHANIYA
**Tagline:** *Beyond Conversations. Towards Intelligence.*
**Status:** Phase 1 (Foundation and Architecture) — see [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)

> Scope note: DIVU AI is a modular AI agent platform designed for long-term expansion and
> AGI-oriented *research*. It is **not** AGI and is **not** claimed to be superintelligent.
> Every capability in this repository is either (a) implemented and tested here, or
> (b) explicitly marked as not-yet-implemented. Nothing is faked.

---

## 1. Architectural principles

| # | Principle | Consequence in code |
|---|-----------|---------------------|
| 1 | **Provider independence** | All models sit behind one `LLMProvider` protocol. No provider SDK type appears in a service signature. Feature support is declared per-model via a capability matrix, never assumed. |
| 2 | **Separation of concerns** | `frontend/` (Next.js), `backend/` (FastAPI), `addons/` (isolated SDK packages). No business logic in routers; routers → services → repositories. |
| 3 | **Portability first** | The platform runs on Postgres+pgvector+Redis in production and on SQLite + in-memory cache + local object storage in dev/CI. The same test suite runs in both. |
| 4 | **Extensibility without risk** | Extensions (add-ons, tools, agents, models, workflows) are data-driven registry entries validated against a manifest, sandboxed, tested, and only activated after explicit approval. |
| 5 | **Fail-safe, not fail-silent** | Timeouts, retries with jitter, circuit breakers, fallbacks, and a strict error envelope. Errors are structured, logged with a request id, and never leak secrets. |
| 6 | **Observability by default** | Structured logs, audit log rows, token/cost usage rows, `/metrics` (Prometheus), and health/readiness probes from day one. |
| 7 | **Security as a layer, not a feature** | AuthN, RBAC, encrypted secrets at rest, rate limits, input validation, prompt-injection screening, audit logging, resource quotas. |
| 8 | **Vertical slices per phase** | Each phase is independently runnable and testable; later phases never silently break earlier ones (CI runs the full suite every time). |

---

## 2. High-level topology

```
                        ┌──────────────────────────────────────────────┐
   Browser / mobile ───▶│  frontend/  Next.js 15 (App Router, TS, TW)  │
                        └───────────────────────┬──────────────────────┘
                                                │  HTTPS, relative /api/* (dev: Next rewrite proxy)
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │  backend/  FastAPI                            │
                        │  ┌────────────────────────────────────────┐  │
                        │  │ Middleware chain                        │  │
                        │  │ request-id → access log → CORS →        │  │
                        │  │ rate limit → auth context → errors      │  │
                        │  └───────────────┬────────────────────────┘  │
                        │  ┌───────────────▼────────────────────────┐  │
                        │  │ API layer (routers: thin, validated)    │  │
                        │  └───────────────┬────────────────────────┘  │
                        │  ┌───────────────▼────────────────────────┐  │
                        │  │ Service layer (all business logic)      │  │
                        │  │  AI Engine · Memory · Agents · RAG ·    │  │
                        │  │  Multimodal · Research · Add-ons · Eval │  │
                        │  └───────────────┬────────────────────────┘  │
                        │  ┌───────────────▼────────────────────────┐  │
                        │  │ Repository + DB layer (SQLAlchemy 2.0)  │  │
                        │  └───────────────┬────────────────────────┘  │
                        └──────────────────┼───────────────────────────┘
                                           │
        ┌──────────────┬───────────────────┼──────────────────┬──────────────────┐
        ▼              ▼                   ▼                  ▼                  ▼
   PostgreSQL     pgvector           Redis              Object Storage     LLM providers
   (system of    (embedding        (cache, rate        (local dir or S3)   (OpenAI, Anthropic,
    record)       index)            limit, queues,      uploads, artifacts  Google, local/
                                    pub/sub)                                self-hosted, mock)
```

---

## 3. Backend module map

```
backend/app/
├── core/            config, logging, errors, ids, time, feature flags
├── security/        passwords, tokens(JWT), encryption, rbac, rate_limit,
│                    audit, injection screening, sandbox (subprocess limits)
├── db/              engine/session, declarative base, mixins, models, repositories
├── schemas/         Pydantic v2 request/response contracts (versioned)
├── api/
│   ├── deps.py      auth, db session, pagination, role guards
│   └── routers/     health, auth, users, chat, models, agents, memory,
│                    knowledge, addons, devstudio, research, admin, system
├── ai/              providers/(openai, anthropic, google, mock), router,
│                    capabilities, pricing, usage, retry/fallback, streaming
├── memory/          session, conversation, long-term, episodic, knowledge, retrieval
├── agents/          framework (registry, runner, tools), builtin agents
├── orchestration/   manager agent, task graph, messaging, aggregation
├── rag/             extract → clean → chunk → embed → index → retrieve → rerank → cite
├── multimodal/      text, image, audio, speech, pdf, document, video interfaces
├── research/        search, paper analysis, literature review, citations, reports
├── addons/          sdk, registry, validator, scanner, sandbox runner, lifecycle
├── eval/            harness, datasets, metrics (quality, RAG, citations, cost)
└── observability/   metrics, tracing hooks, health probes
```

### Request lifecycle (chat, target end-state)

```
HTTP/SSE
  → rate limit + auth (JWT or API key) + RBAC scope check
  → InputProcessing      (normalize, language detect, modality dispatch, injection screening)
  → ContextConstruction  (session memory + conversation window + retrieved memory/RAG, token budgeted)
  → IntentClassification (route: chat | research | code | math | tool | workflow)
  → Planning             (single-shot | tool loop | multi-agent plan; bounded steps)
  → ModelSelection       (capability + cost + latency + health + policy based routing)
  → ToolSelection        (registry match, permission check, argument schema validation)
  → Execution            (provider call with timeout/retry/fallback; tools in sandbox)
  → ResultObservation    (validate tool output, detect loops, enforce step/limit budget)
  → ResponseGeneration   (stream tokens; structure output; attach citations)
  → QualityEvaluation    (self-critique / rubric scoring, optional reviewer agent; logged)
  → Persistence          (messages, usage events, cost, audit, memory writes)
```

Each stage is an independently testable unit with a defined input/output contract.

---

## 4. Data model (overview; full reference in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md))

| Domain | Tables |
|--------|--------|
| Identity & access | `users`, `roles`, `user_roles`, `refresh_tokens`, `api_keys`, `provider_credentials` |
| Safety & ops | `audit_logs`, `usage_events`, `system_events` |
| Conversations | `conversations`, `messages`, `attachments`, `message_citations` |
| AI registry | `model_profiles`, `provider_health` |
| Memory | `memory_items`, `memory_episodes`, `memory_embeddings` |
| Knowledge (RAG) | `documents`, `document_chunks`, `document_ingestions` |
| Agents | `agents`, `agent_runs`, `agent_steps`, `tools` |
| Orchestration | `workflows`, `workflow_runs`, `tasks`, `agent_messages` |
| Add-ons | `addons`, `addon_versions`, `addon_installations`, `addon_test_results` |
| Evaluation | `eval_suites`, `eval_runs`, `eval_results` |

Migrations: **Alembic** (async), one revision per phase, always reversible (`down_revision` implemented).

---

## 5. Cross-cutting contracts

**Error envelope (all 4xx/5xx):**
```json
{
  "error": {
    "code": "permission_denied",
    "message": "This action requires the 'admin' role.",
    "details": {"required_role": "admin"},
    "request_id": "8f2c…",
    "timestamp": "2026-11-07T10:11:12Z"
  }
}
```

**Success envelope for list endpoints:** `{ "items": [...], "page": 1, "page_size": 50, "total": 137 }`

**Ids:** UUIDv4 strings, generated server-side. **Timestamps:** UTC, ISO-8601 with `Z`.

**Streaming:** Server-Sent Events for tokens (`event: delta | tool_call | citation | done | error`).

---

## 6. Configuration & secrets

Single source of truth: `DIVU_`-prefixed environment variables, loaded by
`pydantic-settings` (`backend/app/core/config.py`), with `.env` support for local dev.
`.env.example` documents every variable; **no secret is ever committed** — `divu secrets check`
fails the build if a required secret is missing outside development, and a redaction filter
scrubs known secret values from every log line.

---

## 7. Phase status legend

Implemented ✅ · Partially implemented 🟡 · Designed but not implemented ⚪ · Not started ○

Current status is tracked per phase in [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) and in
the phase report `docs/phases/PHASE_*.md`.
