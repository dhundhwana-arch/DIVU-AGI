# DIVU AI — Database Schema

Engine: **PostgreSQL 16 + pgvector** in production, **SQLite** (aiosqlite) for development and CI.
Access is exclusively through SQLAlchemy 2.0 ORM models in `backend/app/db/models/`; migrations are
Alembic revisions in `backend/migrations/versions/`.

## Conventions

| Convention | Rule |
|---|---|
| Primary keys | UUIDv4 stored as `VARCHAR(36)`, generated application-side (`app.core.ids.new_id`) |
| Timestamps | `TZDateTime`: stored as **naive UTC**, returned as timezone-aware UTC on both backends |
| JSON | `JSON` column type (Postgres `jsonb` via `postgresql.JSONB` when the dialect is Postgres) |
| Naming | Explicit constraint names via `MetaData(naming_convention)` → stable, reversible migrations |
| Deletes | Foreign keys use `ON DELETE CASCADE` for owned rows; user deletion clears `user_roles` explicitly so the same code path works on SQLite (see `UserService.delete_user`) |
| Migrations | One revision per phase; every revision implements `downgrade()`; `render_as_batch=True` for SQLite |
| Secrets | Never stored in plaintext — `provider_credentials.encrypted_value` is Fernet-encrypted |

## Phase 1 tables (implemented)

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUIDv4 |
| `email` | VARCHAR(320) UNIQUE, indexed | stored lower-cased by the service layer |
| `full_name` | VARCHAR(255) | |
| `hashed_password` | VARCHAR(512) | PBKDF2-HMAC-SHA256, `iterations$salt$hash` |
| `is_active` | BOOLEAN | deactivated users cannot log in |
| `is_superuser` | BOOLEAN | bypasses all role checks |
| `timezone` / `locale` | VARCHAR(64) / VARCHAR(16) | defaults `UTC` / `en` |
| `last_login_at` | DATETIME | |
| `failed_login_count` | INTEGER | reset on success |
| `locked_until` | DATETIME | set after `max_failed_logins` |
| `created_at` / `updated_at` | DATETIME | |

### `roles` · `user_roles`
| Table | Columns |
|---|---|
| `roles` | `id` PK, `name` UNIQUE, `description`, `is_system`, timestamps |
| `user_roles` | `user_id` FK→users, `role_id` FK→roles, composite PK |

Default roles: `admin`, `developer`, `user`, `viewer` (created by `UserService.ensure_default_roles`).

### `refresh_tokens`
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | equals the JWT `jti` |
| `user_id` | FK→users, indexed | |
| `token_hash` | VARCHAR(128) UNIQUE | SHA-256 of the raw token; the raw token is never stored |
| `family_id` | VARCHAR(36), indexed | rotation family; reuse revokes the whole family |
| `expires_at` / `created_at` / `revoked_at` | DATETIME | |
| `replaced_by` | VARCHAR(36) | id of the token issued at rotation |
| `used` | BOOLEAN | set when consumed |
| `user_agent` / `ip_address` | VARCHAR | audit context |

### `api_keys`
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `user_id` | FK→users, indexed | |
| `name` | VARCHAR(120) | |
| `prefix` | VARCHAR(16), indexed | first 8 hex chars of the key, used to look the record up |
| `hashed_key` | VARCHAR(128) UNIQUE | SHA-256 of the full key |
| `scopes` | JSON | e.g. `["chat:read","chat:write"]` |
| `expires_at` / `last_used_at` / `revoked_at` | DATETIME | |
| `is_active` | BOOLEAN | |

Key format: `dvk_<prefix>_<secret>` — shown once at creation, never recoverable.

### `provider_credentials` (encrypted secrets at rest)
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `user_id` | FK→users, nullable | null = system-wide credential |
| `provider` | VARCHAR(64), indexed | `openai`, `anthropic`, `google`, … |
| `label` | VARCHAR(120) | |
| `encrypted_value` | TEXT | Fernet token, prefixed `enc:v1:` |
| `masked_value` | VARCHAR(64) | display-only, e.g. `***7890` |
| `is_active` | BOOLEAN | |
| `last_verified_at` | DATETIME | |

### `audit_logs` (append-only at the application layer)
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `created_at` | DATETIME, indexed | |
| `actor_id` | VARCHAR(36), indexed | null for anonymous/system actions |
| `actor_email`, `actor_type` | VARCHAR | `user` \| `system` \| `agent` |
| `action` | VARCHAR(80), indexed | canonical vocabulary in `app/services/audit.py` |
| `outcome` | VARCHAR(32) | `success` \| `failure` \| `denied` \| `blocked` |
| `resource_type`, `resource_id` | VARCHAR | |
| `ip_address`, `user_agent`, `request_id` | VARCHAR | correlation |
| `message` | TEXT | |
| `metadata_json` | JSON | structured details |

### `usage_events` (token, cost and latency accounting)
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `created_at` | DATETIME, indexed | |
| `user_id`, `api_key_id`, `conversation_id`, `agent_id` | VARCHAR(36), indexed where hot | |
| `provider`, `model` | VARCHAR, indexed | |
| `operation` | VARCHAR(64) | `chat`, `embedding`, `rerank`, `tool`, … |
| `input_tokens`, `output_tokens`, `total_tokens` | INTEGER | |
| `cost_usd` | FLOAT | from the pricing table (Phase 3) |
| `latency_ms` | INTEGER | |
| `status`, `error_code` | VARCHAR | |

## Tables planned for later phases

Added by their own Alembic revisions — the schema above is the reviewed Phase 1 baseline.

| Phase | Tables |
|---|---|
| 3 — Chat & routing | `conversations`, `messages`, `attachments`, `message_citations`, `model_profiles`, `provider_health` |
| 4 — Memory & RAG | `memory_items`, `memory_episodes`, `memory_embeddings`, `documents`, `document_chunks`, `document_ingestions` |
| 5-6 — Agents & tools | `agents`, `agent_runs`, `agent_steps`, `tools` |
| 7 — Studio & add-ons | `addons`, `addon_versions`, `addon_installations`, `addon_test_results` |
| 8-9 — Multimodal & orchestration | `media_assets`, `workflows`, `workflow_runs`, `tasks`, `agent_messages` |
| 10 — Evaluation | `eval_suites`, `eval_runs`, `eval_results` |

## Operational notes

* **Migrations:** `make migrate` (`alembic upgrade head`). Production deployments run this as a
  pre-start job, never implicitly at import time.
* **Backups:** nightly `pg_dump` (custom format) plus continuous WAL archiving; object storage is
  versioned. Restore is rehearsed quarterly (see DEPLOYMENT_GUIDE.md).
* **Indexing:** every foreign key plus the hot query paths (`audit_logs.created_at`,
  `usage_events.user_id`, `messages.conversation_id`) is indexed; pgvector uses HNSW indexes that
  are created in the Phase 4 revision.
