import fs from "node:fs";
import path from "node:path";
import Link from "next/link";
import { InstallButton } from "@/components/InstallButton";

// Read the package metadata per request so the page never advertises a file that is not there.
export const dynamic = "force-dynamic";

const PACKAGE_PATH = path.join(process.cwd(), "public", "downloads", "divu-ai-app.zip");
const PACKAGE_URL = "/downloads/divu-ai-app.zip";

function readPackage() {
  try {
    const stat = fs.statSync(PACKAGE_PATH);
    return {
      available: stat.size > 0,
      sizeMb: stat.size / (1024 * 1024),
      updated: stat.mtime.toISOString().slice(0, 10),
    };
  } catch {
    return { available: false, sizeMb: 0, updated: null as string | null };
  }
}

const STEPS = [
  {
    title: "1 · Install from this page (instant)",
    body: "Open the site on your phone or desktop browser and use the Install button. DIVU AI is added to your home screen and opens in a standalone window with no browser chrome.",
    action: "install" as const,
  },
  {
    title: "2 · Download the package (keep it forever)",
    body: "A zip containing the complete application: Next.js frontend, FastAPI backend, database migrations, tests, operator CLI and a one-command start script. Runs on macOS, Linux and Windows with Python 3.11 and Node 22.",
    action: "download" as const,
  },
  {
    title: "3 · Run your own instance",
    body: "Unzip, run ./start.sh (or start.bat on Windows), then open http://localhost:3000. It boots with SQLite and an in-memory cache, so no database server is required. Switch to PostgreSQL, Redis and S3 when you are ready.",
    action: null,
  },
];

const NOTES = [
  {
    title: "Android APK",
    body: "A true APK can be generated from this PWA with PWABuilder or Bubblewrap (the same tooling Google uses for Trusted Web Activities). No Android SDK is required in this environment, so the APK is not shipped here — the installable PWA is functionally equivalent on Android.",
  },
  {
    title: "iOS",
    body: "Safari does not expose an install prompt. Use Share → Add to Home Screen; the app then runs full screen with its own icon and offline shell.",
  },
  {
    title: "Offline behaviour",
    body: "The app shell, icons and static assets are cached, so the installed app always opens. Live features (status, sign-in, screening) reconnect to your backend when the network returns.",
  },
];

export default function DownloadPage() {
  const pkg = readPackage();

  return (
    <div className="space-y-12">
      <section className="panel p-8 md:p-10">
        <p className="panel-title">Install</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
          Put DIVU AI on your home screen
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300">
          DIVU AI is a progressive web app: one codebase that installs like a native app on Android,
          iOS, Windows, macOS and Linux, and updates itself in the background. Choose the route that
          suits you — or do both.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <InstallButton className="btn-primary" />
          {pkg.available ? (
            <a className="btn-ghost" href={PACKAGE_URL} download>
              Download DIVU-AI-app.zip
            </a>
          ) : (
            <span className="badge-off" title="Build it with: make package">
              Package not built yet
            </span>
          )}
          <Link href="/app" className="text-sm text-slate-400 hover:text-white hover:underline">
            Skip and open the workspace
          </Link>
        </div>

        <p className="mt-4 text-xs text-slate-500">
          {pkg.available
            ? `Package built ${pkg.updated} · ${pkg.sizeMb.toFixed(2)} MB. Regenerate any time with: make package`
            : "The downloadable package is a build artifact and is not committed. From the repository root run: make package"}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {STEPS.map((step) => (
          <article key={step.title} className="panel flex flex-col p-5">
            <h2 className="text-sm font-semibold text-white">{step.title}</h2>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-400">{step.body}</p>
            {step.action === "install" && (
              <div className="mt-4">
                <InstallButton className="btn-ghost" />
              </div>
            )}
            {step.action === "download" &&
              (pkg.available ? (
                <a className="btn-ghost mt-4" href={PACKAGE_URL} download>
                  Download zip
                </a>
              ) : (
                <pre className="mt-4 rounded-xl border border-white/10 bg-ink-800/60 px-3 py-2 font-mono text-xs text-slate-300">
                  make package
                </pre>
              ))}
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2 className="text-base font-semibold text-white">What is in the package</h2>
          <span className="text-xs text-slate-500">Complete source, no compiled binaries</span>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2">
          <ul className="space-y-2 text-sm text-slate-300">
            {[
              "Next.js 15 frontend with PWA manifest, service worker and icon set",
              "FastAPI backend: auth, RBAC, audit, rate limiting, injection screening",
              "Alembic migrations (PostgreSQL + pgvector or SQLite)",
              "62-test suite, ruff configuration and GitHub Actions CI",
              "Operator CLI: check-config, seed, create-admin, db-upgrade, run",
              "Docker Compose stack: Postgres+pgvector, Redis, MinIO",
              "Full documentation set: architecture, API, schema, security, deployment",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                {item}
              </li>
            ))}
          </ul>
          <div className="rounded-xl border border-white/10 bg-ink-800/60 p-4">
            <p className="text-xs uppercase tracking-wider text-slate-500">Quick start</p>
            <pre className="mt-2 overflow-x-auto font-mono text-xs leading-relaxed text-slate-300">
{`unzip divu-ai-app.zip
cd divu-ai
./start.sh          # or: start.bat on Windows
# web  → http://localhost:3000
# api  → http://localhost:8000/docs`}
            </pre>
            <p className="mt-3 text-xs text-slate-500">
              Demo login: <span className="text-slate-300">demo@divu.ai</span> /{" "}
              <span className="text-slate-300">Demo!Passphrase1</span>
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {NOTES.map((note) => (
          <div key={note.title} className="panel p-5">
            <h3 className="text-sm font-semibold text-white">{note.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{note.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
