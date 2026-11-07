# DIVU AI — Add-on SDK Guide

> **Status: design document.** The Add-on SDK and Registry are implemented in **Phase 7**. This
> guide is published now so the contract is stable before the first add-on is written. The
> principles below are non-negotiable and already shape the Phase 1 security layer.

## 1. Why add-ons are isolated

An add-on is **untrusted code** running next to a system that holds credentials, memory and
user data. Therefore:

* AI-generated add-on code is **never automatically trusted or deployed**. It is generated,
  scanned, sandboxed and then requires **explicit human approval** before activation.
* A failing add-on must never break the core application. The supervisor disables an extension
  that crashes, exceeds its resource limits, or fails its health check, and records why.
* Add-ons run with declared, minimal permissions and hard resource limits.

## 2. Manifest

Every add-on ships `addon.yaml`:

```yaml
id: com.example.weather            # reverse-DNS, immutable after publication
name: Weather Lookup
version: 1.0.0                      # semver
description: Adds a current-weather tool backed by a public API.
entrypoint: main:register           # module:callable returning the add-on surface
author: Example Labs
license: MIT

dependencies:                       # allow-listed packages only
  - httpx>=0.28,<1

permissions:
  network: ["api.weather.example"]  # exact hosts; no wildcards
  tools: ["register_tool"]
  memory: ["read:session"]
  storage: ["read:addon", "write:addon"]

limits:
  cpu_seconds_per_call: 2
  memory_mb: 128
  timeout_seconds: 5
  max_calls_per_minute: 60

min_platform_version: "0.7.0"
tests:
  command: pytest -q tests
```

Unknown permissions, wildcard hosts, or a `dependencies` entry outside the allow-list **fail
validation** — the add-on never reaches the sandbox.

## 3. SDK surface

```python
from divu_sdk import AddonContext, ToolResult, tool

@tool(
    name="weather.current",
    description="Current weather for a city.",
    arguments={                                   # JSON Schema
        "type": "object",
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
    },
)
async def current_weather(ctx: AddonContext, city: str) -> ToolResult:
    response = await ctx.http.get(                # only allow-listed hosts are reachable
        "https://api.weather.example/v1/current", params={"q": city}
    )
    return ToolResult.ok(
        content={"temp_c": response.json()["temp_c"]},
        citation=response.url,                    # citations are mandatory for external data
    )

def register(ctx: AddonContext) -> None:          # manifest entrypoint
    ctx.register_tool(current_weather)
    ctx.on_disable(lambda: ctx.logger.info("weather add-on disabled"))
```

The context exposes only: `http` (host-restricted), `storage` (addon-scoped keys), `memory`
(declared scopes), `logger` (redacted), `metrics`, and registration hooks for tools, agents,
models and workflows. There is **no** access to the database session, the application settings or
another add-on's storage.

## 4. Lifecycle

```
create → validate → scan → sandbox test → approve → install → register → activate
   │         │         │          │           │          │          │
   │         │         │          │           │          │          └─ registry entry becomes resolvable
   │         │         │          │           │          └──────────── files copied, deps installed
   │         │         │          │           └──────────────────────── explicit human approval (audit logged)
   │         │         │          └──────────────────────────────────── tests run in the sandbox; results stored
   │         │         └─────────────────────────────────────────────── static scan: forbidden imports, network
   │         └───────────────────────────────────────────────────────── manifest + permission validation
   └────────────────────────────────────────────────────────────────── scaffold (optionally AI-assisted)
```

Each transition is recorded: `addon_installations` holds the state, `addon_test_results` holds the
sandbox output, and `audit_logs` records approvals and activations.

**Version management and rollback.** Every install creates a version row. Rollback reinstalls the
previous version's artifacts, re-runs validation, and records the event; the previous version stays
available so rollback is always possible.

## 5. Validation and scanning rules (fail closed)

Rejected automatically:

* imports of `os.system`, `subprocess`, `socket`, `ctypes`, `pickle`, `eval`/`exec`,
  `importlib` outside the declared entrypoint, or direct DB drivers;
* network access to any host not in `permissions.network`;
* filesystem access outside the add-on's storage namespace;
* manifest fields that are missing, malformed, or request more than the allow-list;
* test commands that fail, time out, or exceed the declared limits.

## 6. Sandbox test

Tests run in a subprocess with: no network except the allow-list, memory/CPU rlimits, a wall-clock
timeout, a non-root user and a temporary filesystem. Output is captured into `addon_test_results`
and shown in the Developer Studio before approval.

## 7. Publishing checklist

1. `id` is unique and reverse-DNS styled; `version` is semver.
2. Permissions are minimal; network hosts are exact.
3. Arguments are described with JSON Schema and validated at runtime.
4. Every external fact carries a citation.
5. Tests cover success, failure and permission-denied paths.
6. Resource limits are declared and respected.

## 8. Implemented today

Phase 1 provides the foundations add-ons will be validated against: encrypted credential storage ✅,
RBAC and scopes ✅, audit logging ✅, rate limiting ✅, prompt-injection screening ✅, and the
append-only `audit_logs` table ✅. The SDK package, registry, scanner, sandbox runner and
Developer Studio UI arrive in Phase 7.
