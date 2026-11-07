"use client";

import type { ReadyResponse, SystemInfo } from "@/lib/api";

export interface SystemState {
  loading: boolean;
  info: SystemInfo | null;
  health: ReadyResponse | null;
  error: string | null;
  checkedAt: string;
}

export function SystemPanel({ state, onRefresh }: { state: SystemState; onRefresh: () => void }) {
  const { loading, info, health, error, checkedAt } = state;

  if (loading && !info) {
    return (
      <section className="panel p-5">
        <p className="text-sm text-slate-400">Contacting the DIVU AI backend…</p>
      </section>
    );
  }

  if (error || !info || !health) {
    return (
      <section className="panel p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-white">Backend unreachable</h2>
            <p className="mt-1 max-w-prose text-sm text-slate-400">
              The API did not respond. Start it with{" "}
              <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">make dev-backend</code>{" "}
              and try again. This panel reports real probe results — nothing is simulated.
            </p>
            <p className="mt-2 break-words font-mono text-xs text-rose-300">{error}</p>
          </div>
          <button type="button" className="btn-ghost shrink-0" onClick={onRefresh}>
            Retry
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="text-base font-semibold text-white">Platform status</h2>
          <p className="text-xs text-slate-500">Live data from /system/info and /health/ready</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={health.ready ? "badge-ok" : "badge-warn"}>
            {health.ready ? "Ready" : "Degraded"}
          </span>
          <button type="button" className="btn-ghost" onClick={onRefresh} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-6 p-5 md:grid-cols-2">
        <dl>
          <div className="kv">
            <dt className="kv-key">Version</dt>
            <dd className="kv-value">
              {info.version} <span className="text-slate-500">({info.phase})</span>
            </dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Environment</dt>
            <dd className="kv-value">{info.environment}</dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Database</dt>
            <dd className="kv-value">{info.database}</dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Cache</dt>
            <dd className="kv-value">{info.cache}</dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Storage</dt>
            <dd className="kv-value">{info.storage}</dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Providers</dt>
            <dd className="kv-value">{info.providers.join(", ")}</dd>
          </div>
          <div className="kv">
            <dt className="kv-key">Checked at</dt>
            <dd className="kv-value">{checkedAt}</dd>
          </div>
        </dl>

        <div>
          <p className="panel-title mb-2">Dependency probes</p>
          <ul className="space-y-2">
            {health.components.map((component) => (
              <li
                key={component.name}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2"
              >
                <span className="text-sm capitalize text-slate-300">
                  {component.name.replace("_", " ")}
                </span>
                <span className="flex items-center gap-2 text-right">
                  <span className="truncate text-xs text-slate-500">{component.detail}</span>
                  <span className={component.healthy ? "badge-ok" : "badge-warn"}>
                    {component.healthy ? "ok" : "down"}
                  </span>
                </span>
              </li>
            ))}
          </ul>

          <p className="panel-title mb-2 mt-4">Capabilities</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(info.capabilities).map(([name, enabled]) => (
              <span key={name} className={enabled ? "badge-ok" : "badge-off"}>
                {name.replace("_", " ")}: {enabled ? "on" : "off"}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
