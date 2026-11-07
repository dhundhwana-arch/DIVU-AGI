"use client";

import type { SystemInfo } from "@/lib/api";

const PHASES: Array<{ key: string; label: string; phase: string }> = [
  { key: "chat", label: "AI chat & model router", phase: "Phase 3" },
  { key: "memory", label: "Memory system", phase: "Phase 4" },
  { key: "rag", label: "Knowledge / RAG", phase: "Phase 4" },
  { key: "agents", label: "Agent framework", phase: "Phase 5" },
  { key: "addons", label: "Add-ons & Developer Studio", phase: "Phase 7" },
  { key: "multimodal", label: "Multimodal engine", phase: "Phase 8" },
  { key: "multi_agent", label: "Multi-agent collaboration", phase: "Phase 9" },
];

export function FeatureMatrix({ info }: { info: SystemInfo }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="text-base font-semibold text-white">Feature flags</h2>
        <span className="text-xs text-slate-500">Reported by the API</span>
      </div>
      <ul className="divide-y divide-white/5">
        {PHASES.map(({ key, label, phase }) => {
          const enabled = Boolean(info.features[key]);
          return (
            <li key={key} className="flex items-center justify-between px-5 py-3">
              <span className="text-sm text-slate-200">{label}</span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-slate-500">{phase}</span>
                <span className={enabled ? "badge-ok" : "badge-off"}>
                  {enabled ? "enabled" : "not yet"}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
