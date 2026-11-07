# DIVU AI — Security Guide

Scope: the controls that are **implemented and tested** are marked ✅. Controls designed but not
yet built are marked ○ with the phase that delivers them. This document is the operational
reference; the risk register lives in [PHASE0_ANALYSIS.md](PHASE0_ANALYSIS.md) §6.

## 1. Principles

1. **Least privilege by default** — every route declares the role it needs; ownership checks live
   in the service/repository layer, not in the router.
2. **Secrets never rest in plaintext, never reach logs, never reach the browser.**
3. **Defence in depth for AI-specific attacks** — prompt injection is treated as a data-boundary
   problem, not something a single filter can solve.
4. **Fail safe, and say so** — health and readiness probes report honest component state; the
   rate limiter fails open (availability) while quotas and audits bound the abuse risk.
5. **Everything security-relevant is auditable** — the audit log is append-only at the
   application layer.

## 2. Implemented in Phase 1 ✅

### Identity and access
| Control | Implementation |
|---|---|
| Password storage | PBKDF2-HMAC-SHA256, 600k iterations, 16-byte per-user salt, constant-time verify, opportunistic rehash on login |
| Password policy | Minimum length (12), distinct-character and common-password checks (`app/security/passwords.py`) |
| Tokens | JWT HS256 (RS256-ready), `typ` claim prevents refresh/access confusion, `jti`, short access TTL |
| Refresh rotation | Every refresh issues a new token; reuse revokes the whole `family_id` and writes `auth.token.reuse_detected` |
| Brute-force protection | Failure counter, exponential-ish lockout window (`max_failed_logins`, `lockout_seconds`), audited failures |
| API keys | `dvk_<prefix>_<secret>`, SHA-256 at rest, scopes, expiry, revocation, `last_used_at` |
| RBAC | `require_roles(...)` guard; built-in roles `admin`, `developer`, `user`, `viewer`; superuser bypass; denied access is audited |

### Data protection
| Control | Implementation |
|---|---|
| Encryption at rest | Fernet (AES-128-CBC + HMAC) for credentials, key from `DIVU_ENCRYPTION_KEY`; derived from the app secret in development only |
| Key handling | No secret in source control or in the frontend bundle; `.env` is git-ignored; CI fails on credential-shaped strings |
| Log redaction | A structlog processor redacts sensitive keys and scrubs every configured secret value from all fields |
| Transport | TLS is terminated at the reverse proxy in deployment; cookies/tokens are never logged |

### Abuse and AI-specific defence
| Control | Implementation |
|---|---|
| Rate limiting | Sliding window, per client+path; stricter bucket for `/auth/*`; Redis backend for multi-instance, in-memory for single instance; `Retry-After` on 429 |
| Prompt-injection screening | Weighted pattern engine with per-source thresholds (user 0.6, document/tool 0.35), obfuscation detection (base64, zero-width), audit on block |
| Data/instruction separation | `wrap_untrusted()` marks retrieved content as data (used by RAG from Phase 4) |
| Input validation | Pydantic v2 on every request; length caps; unknown fields rejected |
| SQL safety | Parameterised queries only, via SQLAlchemy; no string-built SQL except the migration round-trip test |

### Observability and response
| Control | Implementation |
|---|---|
| Audit log | `audit_logs` with actor, action, outcome, resource, IP, user agent, request id, metadata; admin query API |
| Request correlation | `X-Request-ID` on every request, echoed in responses and included in error envelopes |
| Metrics | Prometheus `/metrics` (request and dependency instrumentation) |
| Structured logs | JSON in production, console in development, always redacted |

## 3. Designed, not yet implemented ○

| Phase | Control |
|---|---|
| 3 | Per-user token/cost quotas, provider circuit breakers, output secret scanning |
| 4 | Upload hardening (MIME/extension allowlist, magic bytes, size caps, sandbox extraction), PII retention policies, memory export/delete workflows |
| 6 | Sandboxed tool execution (subprocess, rlimits, no network, timeouts, non-root), tool allowlists per agent, egress allowlist |
| 7 | Add-on static scanning, sandbox test, mandatory human approval, kill switch, version rollback, supervisor isolation of failing extensions |
| 10 | MFA/SSO, penetration-test checklist, dependency auditing in CI (`pip-audit`, `npm audit`), WAF rules, SIEM export, DPA/GDPR tooling |

## 4. Threat model (STRIDE-ish summary)

| Threat | Mitigation | Status |
|---|---|---|
| Stolen credentials | Hashing + lockout + rotation + reuse detection + audit | ✅ |
| Token replay | `jti`, expiry, rotation, family revocation | ✅ |
| Privilege escalation | RBAC guards + ownership checks + audited denials | ✅ |
| Secret exfiltration from logs/backups | Redaction + encryption at rest + redacted config endpoint | ✅ |
| Prompt injection (direct) | Screening at 0.6 threshold, system-prompt discipline | ✅ |
| Prompt injection (indirect via documents/tools) | 0.35 threshold + `wrap_untrusted` + citation enforcement | 🟡 screening ✅ / RAG boundaries Phase 4 |
| Malicious extension | Manifest validation, scan, sandbox, human approval | ○ Phase 7 |
| Sandbox escape | rlimits, no network, non-root, timeouts | ○ Phase 6 |
| Cost-based DoS | Rate limits now; per-user quotas and budgets | 🟡 Phase 3 |
| Supply chain | Pinned versions, reproducible installs, CI secret scan | 🟡 audit tools Phase 10 |
| Insider misuse | Audit log, admin actions recorded, no self-deletion | ✅ |

## 5. Operator checklist

**Deployment**
1. `DIVU_APP_ENV=production` — the app refuses to start with a weak/missing `DIVU_SECRET_KEY`,
   without `DIVU_ENCRYPTION_KEY`, with `debug` on, or with public registration enabled.
2. Generate keys:
   ```bash
   python -c "import secrets;print(secrets.token_urlsafe(48))"          # DIVU_SECRET_KEY
   python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"  # DIVU_ENCRYPTION_KEY
   ```
3. Terminate TLS at the proxy; forward `X-Forwarded-For` (the rate limiter keys on it).
4. Restrict CORS to your own origins (`DIVU_CORS_ORIGINS`); leave the regex empty unless needed.
5. Run migrations as a pre-start job (`alembic upgrade head`), never implicitly at import.

**Operations**
* Rotate the encryption key by re-encrypting `provider_credentials` (a management command ships
  with Phase 3) — never by editing rows by hand.
* Monitor `/health/ready`, the 429 rate on `/api/v1/auth/*`, and `security.*` audit actions.
* Back up nightly and rehearse a restore (see DEPLOYMENT_GUIDE.md).

**Incident response**
1. Revoke the affected sessions: `DELETE` the user's API keys and revoke refresh-token families
   (a `promote`/`revoke` management command ships with Phase 3; today, deactivate the user).
2. Pull the audit trail: `GET /api/v1/audit?actor_id=<id>`.
3. Rotate `DIVU_SECRET_KEY` (invalidates all sessions) and `DIVU_ENCRYPTION_KEY` if the database
   may have leaked.
4. Preserve structured logs — they are redacted, so they are safe to attach to reports.

## 6. Reporting

Report vulnerabilities privately to the maintainer (email in the repository profile) with steps to
reproduce and impact. Please do **not** open a public issue for a live vulnerability. Expected
response: acknowledgement within 72 hours, fix or mitigation plan within 14 days.
