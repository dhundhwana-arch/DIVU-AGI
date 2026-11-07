# DIVU AI — Agent Development Guide

> **Status: design document.** The agent framework is implemented in **Phase 5**; the add-on SDK in
> **Phase 7**. This guide is published now so agent and add-on authors can build against a stable
> contract. Items marked **implemented** exist in the repository today.

DIVU AI is a modular AI agent platform. The agent framework is the extension point for
task-specific behaviour; everything an agent can do is expressed through the tool, memory and
model services it is granted.

## 1. What an agent is

An agent is a **persisted configuration** (not code in the core tree) with this schema:

| Field | Type | Purpose |
|---|---|---|
| `id` | UUID | Stable identifier |
| `name` | string | Display name |
| `description` | string | Shown in the agent selector; also used by the router |
| `instructions` | string | System-level behaviour definition |
| `model_config` | object | Provider, model, temperature, max tokens, fallbacks |
| `tools` | list[tool id] | Capabilities the agent may invoke |
| `knowledge_sources` | list[collection id] | RAG collections the agent may retrieve from |
| `permissions` | object | Which resources/scopes the agent acts with |
| `execution_limits` | object | max steps, max tokens, wall-clock timeout, max tool calls |
| `memory_config` | object | Session / long-term / episodic memory settings and retention |
| `evaluation_tests` | list[case] | Cases run before the agent can be marked `active` |
| `status` | enum | `draft` · `testing` · `active` · `disabled` |

Agents are data: they are created through the API or the Developer Studio, validated against this
schema, tested, then activated. No agent code is imported into the core application.

## 2. Agent lifecycle

```
draft → validate → run eval suite → review → active → (monitor) → disabled
```

* A draft agent can be executed only by its author, in a sandbox workspace.
* Promotion to `active` requires a passing evaluation run (recorded in `eval_runs`).
* A failing or abusive agent is disabled automatically by the supervisor; the failure is logged
  and surfaced in the admin dashboard.

## 3. Execution model

```python
run = await agent_runner.run(agent, input=message, principal=principal, session=session)
# → AgentRun(status="completed", steps=[...], usage=..., citations=[...])
```

The runner enforces, in order:

1. **Permission check** — the caller must have a scope that covers the agent.
2. **Context construction** — instructions + session memory + retrieved knowledge (token budgeted).
3. **Planning** — single-shot, tool loop, or delegated plan (bounded step count).
4. **Model selection** — capability-aware routing with fallback providers.
5. **Tool execution** — schema-validated arguments, sandboxed, permission-scoped.
6. **Observation** — validate tool output, detect loops, enforce limits.
7. **Response generation** — streamed; citations attached from retrieval, never invented.
8. **Evaluation** — optional reviewer agent; metrics recorded in `usage_events` and `eval_results`.

Hard limits (`execution_limits`) always win: exceeding steps, tokens or wall-clock ends the run
with `status="limit_exceeded"` and a structured explanation.

## 4. Built-in agents (Phase 5)

| Agent | Responsibility |
|---|---|
| General Assistant | Everyday conversation and task routing |
| Research Agent | Search, paper analysis, literature review, citation management |
| Coding Agent | Code generation, refactors, test authoring, sandboxed execution |
| Mathematics Agent | Symbolic and numeric reasoning with tool-verified steps |
| Data Analysis Agent | Tabular analysis, statistics, charting over uploaded data |
| Document Analysis Agent | Long-document understanding with grounded citations |
| Planning Agent | Task decomposition, scheduling, dependency handling |
| Quality Review Agent | Independent review of another agent's output against a rubric |

## 5. Writing your own agent

1. **Describe, don't hard-code.** Create the agent through `POST /api/v1/agents` (Phase 5) or the
   Developer Studio (Phase 7).
2. **Grant the minimum.** Attach only the tools, knowledge collections and scopes it needs.
3. **Set limits.** Every agent declares `max_steps`, `max_tokens` and `timeout_seconds`.
4. **Ship tests.** Provide `evaluation_tests`: input → expected properties (not exact strings).
   The eval harness measures task completion, citation accuracy and cost.
5. **Handle failure.** An agent must degrade to a clear message; it must never fabricate a citation
   or silently drop a tool error.
6. **Package as an add-on** if it needs new code (see [ADDON_SDK_GUIDE.md](ADDON_SDK_GUIDE.md));
   packaged agents are scanned, sandboxed and require explicit approval.

## 6. Testing your agent

* Unit-test any add-on code you ship (`pytest`).
* Provide evaluation cases; CI runs them and records results.
* Run the security checks: an agent whose instructions request forbidden capabilities fails
  validation; an add-on importing forbidden modules fails the scan.

## 7. Implemented today

The Phase 1 foundation that agents build on: authentication and RBAC ✅, audit logging ✅,
usage accounting schema ✅ (`usage_events`), encrypted credential vault ✅, rate limiting ✅,
prompt-injection screening ✅. Agent CRUD, the runner and the eight built-ins arrive in Phase 5.
