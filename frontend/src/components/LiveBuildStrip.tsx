/**
 * Server component: renders the live build status reported by the DIVU AI backend.
 *
 * The call happens on the server (never exposing backend internals to the browser) and is
 * revalidated every 30 seconds. If the API is unreachable the strip degrades to an honest
 * "unreachable" state instead of showing invented numbers.
 */

interface SystemInfo {
  version: string;
  phase: string;
  environment: string;
  database: string;
  features: Record<string, boolean>;
  providers: string[];
}

async function loadInfo(): Promise<SystemInfo | null> {
  const base = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${base}/api/v1/system/info`, {
      next: { revalidate: 30 },
    });
    if (!response.ok) return null;
    return (await response.json()) as SystemInfo;
  } catch {
    return null;
  }
}

export async function LiveBuildStrip() {
  const info = await loadInfo();

  if (!info) {
    return (
      <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs text-slate-400">
        Backend not reachable from this page — start the API to see live build status.
      </div>
    );
  }

  const enabled = Object.values(info.features).filter(Boolean).length;

  return (
    <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <dt className="text-[11px] uppercase tracking-wider text-slate-500">Build</dt>
        <dd className="mt-1 font-medium text-slate-100">
          v{info.version} <span className="text-slate-500">· {info.phase}</span>
        </dd>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <dt className="text-[11px] uppercase tracking-wider text-slate-500">Database</dt>
        <dd className="mt-1 font-medium text-slate-100">{info.database}</dd>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <dt className="text-[11px] uppercase tracking-wider text-slate-500">Providers</dt>
        <dd className="mt-1 font-medium text-slate-100">{info.providers.join(", ")}</dd>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <dt className="text-[11px] uppercase tracking-wider text-slate-500">Features live</dt>
        <dd className="mt-1 font-medium text-slate-100">
          {enabled} of {Object.keys(info.features).length}
        </dd>
      </div>
    </dl>
  );
}
