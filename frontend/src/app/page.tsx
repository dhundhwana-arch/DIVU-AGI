import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { InstallButton } from "@/components/InstallButton";
import { LiveBuildStrip } from "@/components/LiveBuildStrip";

const CAPABILITIES = [
  {
    title: "Provider-independent AI core",
    body: "One interface for every model. Capability matrices declare what each model actually supports, so vision or tool use is never assumed.",
    tag: "Engine",
  },
  {
    title: "Intelligent model routing",
    body: "Requests are routed on capability, cost, latency and provider health, with timeouts, retries and automatic fallback.",
    tag: "Router",
  },
  {
    title: "Memory that you control",
    body: "Session, conversation, long-term, episodic and knowledge memory — inspectable, editable, exportable and deletable at any time.",
    tag: "Memory",
  },
  {
    title: "Grounded retrieval",
    body: "Upload to extract, clean, chunk, embed, index, retrieve and rerank. Answers cite their sources; citations are never invented.",
    tag: "Knowledge",
  },
  {
    title: "Agents with limits",
    body: "A reusable agent framework with permissions, execution limits, tools, knowledge sources and evaluation tests.",
    tag: "Agents",
  },
  {
    title: "Developer Studio and add-ons",
    body: "Build features, agents, models, tools and workflows in-app. Add-ons are validated, scanned, sandboxed and approved before activation.",
    tag: "Extensibility",
  },
];

const PHASES: Array<{ id: string; name: string; status: "done" | "active" | "planned"; note: string }> = [
  { id: "01", name: "Foundation & architecture", status: "done", note: "Config, logging, errors, database, auth, RBAC, audit, rate limiting" },
  { id: "02", name: "Frontend & backend", status: "active", note: "App shell, installable PWA, live status, auth flows" },
  { id: "03", name: "AI chat & model router", status: "planned", note: "Streaming, fallbacks, token and cost tracking" },
  { id: "04", name: "Memory & RAG", status: "planned", note: "Five memory types, full retrieval pipeline with citations" },
  { id: "05", name: "Agent framework", status: "planned", note: "Eight built-in agents with permissions and limits" },
  { id: "06", name: "Tool integration", status: "planned", note: "Registry, schema validation, sandboxed execution" },
  { id: "07", name: "Developer Studio & add-ons", status: "planned", note: "SDK, registry, sandbox testing, versioning, rollback" },
  { id: "08", name: "Multimodal", status: "planned", note: "Images, audio, speech, documents, video" },
  { id: "09", name: "Multi-agent collaboration", status: "planned", note: "Delegation, shared context, review, anti-recursion guards" },
  { id: "10", name: "Evaluation, security & deployment", status: "planned", note: "Eval harness, hardening, Kubernetes, backup drills" },
];

const SECURITY = [
  { title: "Encrypted secrets", body: "Provider credentials are Fernet-encrypted at rest and masked everywhere else." },
  { title: "RBAC and audit", body: "Role-guarded routes, ownership checks, and an append-only audit log for every security event." },
  { title: "Injection defence", body: "Prompt-injection screening with stricter thresholds for documents and tool output." },
  { title: "Redacted logging", body: "Sensitive fields and known secret values are scrubbed from every log line." },
  { title: "Rate limiting", body: "Sliding-window limits with a stricter bucket for authentication, plus lockout after repeated failures." },
  { title: "Honest health probes", body: "Readiness reports each dependency separately and returns 503 when degraded." },
];

export default function HomePage() {
  return (
    <div className="space-y-20 pb-8">
      {/* ---------------------------------------------------------------- Hero */}
      <section className="relative overflow-hidden">
        <div className="grid items-center gap-10 py-10 md:grid-cols-[1.15fr_0.85fr] md:py-16">
          <div>
            <span className="badge-ok">Phase 1 complete · installable app now available</span>
            <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight text-white sm:text-5xl">
              A modular AI ecosystem,
              <br />
              <span className="bg-brand-gradient bg-clip-text text-transparent">
                built to be extended.
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-300">
              Multi-model routing, memory, retrieval, autonomous agents, tools and an internal
              developer studio — delivered phase by phase, with real code and automated tests at
              every step. Install it on your home screen and it opens like a native app.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link href="/app" className="btn-primary">
                Launch workspace
              </Link>
              <InstallButton className="btn-ghost" />
              <Link href="/download" className="text-sm text-slate-400 underline-offset-4 hover:text-white hover:underline">
                Get the app file
              </Link>
            </div>

            <p className="mt-8 text-xs uppercase tracking-[0.22em] text-brand-400">
              Beyond Conversations. Towards Intelligence.
            </p>
            <p className="mt-2 text-sm text-slate-300">
              <span className="font-semibold text-white">DIVYESH BAMBHANIYA</span>
              <span className="text-slate-500"> · Founder &amp; Creator</span>
            </p>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 rounded-[2rem] bg-brand-gradient opacity-20 blur-2xl" />
            <div className="relative rounded-3xl border border-white/10 bg-ink-900/80 p-6 shadow-panel">
              <div className="flex items-center gap-3">
                <BrandMark size={44} />
                <div>
                  <p className="font-semibold text-white">DIVU AI</p>
                  <p className="text-xs text-slate-500">Installs to your home screen</p>
                </div>
              </div>
              <LiveBuildStrip />
              <ul className="mt-5 space-y-2 text-sm text-slate-300">
                {[
                  "Works offline for the app shell",
                  "Standalone window, no browser chrome",
                  "Fast, content-hashed static assets",
                  "Reconnects to the backend automatically",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------ Platform */}
      <section id="platform" className="scroll-mt-24">
        <header className="max-w-2xl">
          <p className="panel-title">Platform</p>
          <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">
            Six subsystems, one architecture
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            Every subsystem is an independent module behind a stable contract, so a capability can be
            upgraded, replaced or disabled without rewriting the platform.
          </p>
        </header>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((item) => (
            <article
              key={item.title}
              className="panel group p-5 transition hover:border-brand-500/40 hover:shadow-glow"
            >
              <span className="badge-off">{item.tag}</span>
              <h3 className="mt-3 text-base font-semibold text-white">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------- Roadmap */}
      <section id="roadmap" className="scroll-mt-24">
        <header className="max-w-2xl">
          <p className="panel-title">Roadmap</p>
          <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">
            Ten phases, each one testable
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            No untested code dumps. Every phase ships implementation, automated tests, documentation
            and an honest report of what is complete and what is not.
          </p>
        </header>

        <ol className="mt-8 grid gap-3 md:grid-cols-2">
          {PHASES.map((phase) => (
            <li
              key={phase.id}
              className="panel flex items-start gap-4 p-4"
            >
              <span className="mt-0.5 font-mono text-xs text-slate-500">{phase.id}</span>
              <div className="flex-1">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-white">{phase.name}</h3>
                  <span
                    className={
                      phase.status === "done"
                        ? "badge-ok"
                        : phase.status === "active"
                          ? "badge-warn"
                          : "badge-off"
                    }
                  >
                    {phase.status === "done" ? "complete" : phase.status === "active" ? "in progress" : "planned"}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{phase.note}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ------------------------------------------------------------ Security */}
      <section id="security" className="scroll-mt-24">
        <header className="max-w-2xl">
          <p className="panel-title">Security</p>
          <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">
            Designed so a mistake is contained
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            Credentials are encrypted, routes are role-guarded, actions are audited, and untrusted
            text is screened before it reaches a model. Controls listed here are implemented and
            covered by tests today.
          </p>
        </header>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SECURITY.map((item) => (
            <div key={item.title} className="panel p-5">
              <h3 className="text-sm font-semibold text-white">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* --------------------------------------------------------------- CTA */}
      <section className="panel overflow-hidden">
        <div className="grid gap-6 p-8 md:grid-cols-[1.3fr_0.7fr] md:items-center md:p-10">
          <div>
            <h2 className="text-2xl font-semibold text-white">Use it on any device</h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
              Add DIVU AI to your home screen for a standalone, offline-capable app. Prefer a file
              you can keep? Download the package with the full source, the operator CLI and a
              one-command start script.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <InstallButton className="btn-primary" />
            <Link href="/download" className="btn-ghost">
              Download package
            </Link>
            <Link href="/app" className="btn-ghost">
              Open the workspace
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
