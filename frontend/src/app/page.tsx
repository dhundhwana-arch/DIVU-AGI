"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { UserResponse } from "@/lib/api";
import { AuthPanel } from "@/components/AuthPanel";
import { FeatureMatrix } from "@/components/FeatureMatrix";
import { SecurityPanel } from "@/components/SecurityPanel";
import { SystemPanel, type SystemState } from "@/components/SystemPanel";

const INITIAL: SystemState = {
  loading: true,
  info: null,
  health: null,
  error: null,
  checkedAt: "—",
};

export default function HomePage() {
  const [state, setState] = useState<SystemState>(INITIAL);
  const [user, setUser] = useState<UserResponse | null>(null);

  const loadSystem = useCallback(async () => {
    setState((previous) => ({ ...previous, loading: true }));
    try {
      const [info, health] = await Promise.all([api.systemInfo(), api.readiness()]);
      setState({
        loading: false,
        info,
        health,
        error: null,
        checkedAt: new Date().toLocaleTimeString(),
      });
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? `${caught.status} ${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : "Unknown error";
      setState({ loading: false, info: null, health: null, error: message, checkedAt: new Date().toLocaleTimeString() });
    }
  }, []);

  useEffect(() => {
    void loadSystem();
    // Restore an existing session on first paint.
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, [loadSystem]);

  return (
    <div className="space-y-8">
      <section className="panel overflow-hidden">
        <div className="grid gap-6 p-8 md:grid-cols-[1.4fr_1fr] md:p-10">
          <div>
            <span className="badge-ok">Phase 1 complete · Phase 2 in progress</span>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              A modular AI ecosystem, built to be extended.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base">
              Multi-model routing, memory, retrieval, autonomous agents, tools, an internal
              developer studio and a sandboxed add-on architecture — delivered phase by phase,
              with real code and automated tests at every step.
            </p>
            <p className="mt-6 text-xs uppercase tracking-[0.22em] text-brand-400">
              Beyond Conversations. Towards Intelligence.
            </p>
            <p className="mt-3 text-sm text-slate-300">
              <span className="font-semibold text-white">DIVYESH BAMBHANIYA</span>
              <span className="text-slate-500"> · Founder &amp; Creator</span>
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-3 self-center">
            {[
              { label: "Backend", value: "FastAPI · SQLAlchemy 2.0" },
              { label: "Frontend", value: "Next.js 15 · TypeScript" },
              { label: "Data", value: "PostgreSQL · pgvector · Redis" },
              { label: "Extensibility", value: "Add-on SDK + sandbox" },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <dt className="text-[11px] uppercase tracking-wider text-slate-500">{item.label}</dt>
                <dd className="mt-1 text-sm text-slate-100">{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <SystemPanel state={state} onRefresh={() => void loadSystem()} />

      <div className="grid gap-8 lg:grid-cols-2">
        <AuthPanel onAuthChange={setUser} />
        <SecurityPanel user={user} />
      </div>

      {state.info && <FeatureMatrix info={state.info} />}
    </div>
  );
}
