"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { UserResponse } from "@/lib/api";
import { AuthPanel } from "@/components/AuthPanel";
import { FeatureMatrix } from "@/components/FeatureMatrix";
import { InstallButton } from "@/components/InstallButton";
import { SecurityPanel } from "@/components/SecurityPanel";
import { SystemPanel, type SystemState } from "@/components/SystemPanel";

const INITIAL: SystemState = {
  loading: true,
  info: null,
  health: null,
  error: null,
  checkedAt: "—",
};

export default function WorkspacePage() {
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
      setState({
        loading: false,
        info: null,
        health: null,
        error: message,
        checkedAt: new Date().toLocaleTimeString(),
      });
    }
  }, []);

  useEffect(() => {
    void loadSystem();
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, [loadSystem]);

  return (
    <div className="space-y-8">
      <section className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <h1 className="text-xl font-semibold text-white">DIVU AI workspace</h1>
          <p className="mt-1 text-sm text-slate-400">
            Live platform status, account access and the security toolkit. Everything on this page
            talks to the real API.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <InstallButton className="btn-primary" />
          <button type="button" className="btn-ghost" onClick={() => void loadSystem()}>
            Refresh status
          </button>
        </div>
      </section>

      <SystemPanel state={state} onRefresh={() => void loadSystem()} />

      <div className="grid gap-8 lg:grid-cols-2">
        <AuthPanel onAuthChange={setUser} />
        <div id="security">
          <SecurityPanel user={user} />
        </div>
      </div>

      {state.info && <FeatureMatrix info={state.info} />}
    </div>
  );
}
