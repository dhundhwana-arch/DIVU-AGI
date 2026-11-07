# DIVU AI — API Documentation

Base URL (development): `http://localhost:8000` · Interactive docs: `/docs` · Metrics: `/metrics`
All versioned routes live under **`/api/v1`**. Health probes are unversioned and unauthenticated.

## 1. Conventions

* **Content type:** `application/json`; requests and responses are UTF-8.
* **Timestamps:** ISO-8601 UTC with a `Z` suffix.
* **Ids:** UUIDv4 strings generated server-side.
* **Pagination:** `?page=1&page_size=50` (max 200) → `{items, page, page_size, total}`.
* **Streaming (Phase 3+):** Server-Sent Events on chat endpoints with `delta | tool_call | citation | done | error` events.

### Error envelope

Every 4xx/5xx response has the same shape. Codes are stable strings; messages are human-readable.

```json
{
  "error": {
    "code": "permission_denied",
    "message": "You do not have permission to perform this action.",
    "details": {"required_roles": ["admin"]},
    "request_id": "8f2c1f…",
    "timestamp": "2026-11-07T10:11:12Z"
  }
}
```

| Status | `code` | Meaning |
|---|---|---|
| 400 | `bad_request` | Malformed or semantically invalid request |
| 401 | `authentication_required`, `invalid_credentials`, `token_invalid` | Missing/bad credentials |
| 403 | `permission_denied`, `feature_disabled` | Authenticated but not allowed |
| 404 | `not_found` | Resource does not exist (or is not owned by the caller) |
| 409 | `conflict` | Duplicate email, state conflict |
| 413 | `resource_limit_exceeded` | Upload/quota limit |
| 422 | `validation_error` | Pydantic validation failed — `details` lists field errors |
| 429 | `rate_limited` | Includes `Retry-After` |
| 502 | `provider_error` | Upstream AI provider failure |
| 503 | `dependency_unavailable` | Database/cache/storage unavailable |
| 500 | `internal_error` | Logged with the `request_id`; never leaks internals |

Every response carries `X-Request-ID`, `X-Response-Time-Ms` and (when rate limiting applies)
`X-RateLimit-Limit` / `X-RateLimit-Remaining`.

### Authentication

Two mutually exclusive methods:

```http
Authorization: Bearer <access token>
X-API-Key: dvk_<prefix>_<secret>
```

Access tokens are short-lived JWTs (`typ=access`, default 15 min). Refresh tokens
(`typ=refresh`, default 14 days) rotate on every use; reuse of a rotated token revokes the entire
session family. API keys are hashed at rest and scoped.

## 2. Health (unauthenticated, exempt from rate limiting)

| Method | Path | Description |
|---|---|---|
| GET | `/health/live` | Liveness: 200 while the process can serve |
| GET | `/health/ready` | Readiness: per-dependency probes; 503 if a hard dependency is down |
| GET | `/health/version` | App name, version, founder |

```json
{
  "status": "ok", "version": "0.1.0", "environment": "development", "ready": true,
  "components": [
    {"name": "database", "healthy": true, "detail": "sqlite", "latency_ms": 1},
    {"name": "object_storage", "healthy": true, "detail": "local:/app/.data/objects", "latency_ms": 0},
    {"name": "cache", "healthy": true, "detail": "memory (in-process, backend=memory)", "latency_ms": 0}
  ]
}
```

## 3. System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/system/info` | public | Brand, version, phase, feature flags, providers, detected capabilities |
| GET | `/api/v1/system/config` | admin | Full configuration with every secret replaced by `***redacted***` |
| GET | `/api/v1/system/me` | admin | Current principal (id, email, roles, auth method) |

## 4. Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | public* | Create an account (`email`, `password`, `full_name`) → 201 |
| POST | `/api/v1/auth/login` | public | Exchange credentials for a token pair |
| POST | `/api/v1/auth/refresh` | public | Rotate the refresh token |
| POST | `/api/v1/auth/logout` | public | Revoke a refresh token |
| GET | `/api/v1/auth/me` | bearer/key | Current profile |
| POST | `/api/v1/auth/change-password` | bearer | Requires the current password |
| POST | `/api/v1/auth/password/check` | public | Validate a password against the policy |
| POST | `/api/v1/auth/api-keys` | bearer | Create a personal API key (secret shown once) |
| GET | `/api/v1/auth/api-keys` | bearer | List your keys (masked) |
| DELETE | `/api/v1/auth/api-keys/{id}` | bearer | Revoke one of your keys |

\* `register` is open when `DIVU_ALLOW_PUBLIC_REGISTRATION=true` (development default); in
production it is disabled and administrators create accounts via `/api/v1/users`.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@divu.ai","password":"Demo!Passphrase1"}'
```

```json
{"access_token":"eyJ…","refresh_token":"eyJ…","token_type":"bearer","expires_in":900,"refresh_expires_in":1209600}
```

Authentication endpoints use a stricter rate-limit bucket (`DIVU_AUTH_RATE_LIMIT_*`, default
10 requests / 60 s per client).

## 5. Users (admin)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/users?page&page_size&query` | Paged user list |
| GET | `/api/v1/users/roles` | Available roles |
| GET | `/api/v1/users/{id}` | Fetch one user |
| POST | `/api/v1/users/{id}/roles` | Replace roles: `{"roles": ["developer"]}` |
| PATCH | `/api/v1/users/{id}/status` | Activate/deactivate: `{"is_active": false}` |
| DELETE | `/api/v1/users/{id}` | Delete a user (cannot delete yourself) |

## 6. Audit (admin)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/audit?page&page_size&action&actor_id&outcome` | Query the audit log |
| GET | `/api/v1/audit/actions` | Canonical action vocabulary |

## 7. Security utilities

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/security/screen` | bearer | Screen text for prompt injection: `{"text": "...", "source": "user\|document\|tool_output"}` |
| GET | `/api/v1/security/policy` | bearer | Current thresholds per source |
| POST | `/api/v1/security/credentials` | bearer | Store an encrypted third-party credential |
| GET | `/api/v1/security/credentials` | bearer | List your credentials (masked) |
| POST | `/api/v1/security/credentials/{id}/reveal` | bearer | Decrypt one credential (audited) |
| DELETE | `/api/v1/security/credentials/{id}` | bearer | Delete a credential |

```json
{"risk_score":1.0,"blocked":true,
 "categories":["instruction_override","system_prompt_extraction"],
 "matches":["Ignore all previous instructions"],"source":"user","threshold":0.6}
```

## 8. Endpoints planned for later phases

Documented here so clients can be built ahead of time; each lands with its phase and is
`404`-free only once the matching feature flag is enabled.

| Phase | Endpoints |
|---|---|
| 3 | `POST /chat/completions` (SSE), `GET /models`, `GET /models/{id}`, `GET /usage/summary` |
| 4 | `POST /knowledge/ingest`, `GET /knowledge/documents`, `POST /knowledge/search`, `GET /memory/*`, `PATCH /memory/{id}`, `DELETE /memory/{id}`, `POST /memory/export` |
| 5 | `GET/POST/PATCH/DELETE /agents`, `POST /agents/{id}/run`, `GET /agents/{id}/runs` |
| 6 | `GET /tools`, `POST /tools/{id}/invoke`, `GET /tools/{id}/schema` |
| 7 | `/devstudio/*` (features, agents, models, apis, tools, knowledge, workflows, add-ons), `/addons/*` (lifecycle, versions, rollback) |
| 8 | `POST /multimodal/{image,audio,speech,document,video}` |
| 9 | `POST /orchestration/runs`, `GET /orchestration/runs/{id}`, `GET /orchestration/runs/{id}/messages` |
| 10 | `/eval/suites`, `/eval/runs`, `/admin/*`, `/backup/*` |

## 9. Versioning and compatibility

* Breaking changes increment the URL prefix (`/api/v2`).
* Additive, optional fields may appear in responses at any time; clients must ignore unknown keys.
* `GET /api/v1/system/info` reports `version`, `phase` and the enabled `features`, which is the
  supported way for a client to detect what the deployment can do.
