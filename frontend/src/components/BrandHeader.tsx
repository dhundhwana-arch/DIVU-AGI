import Link from "next/link";

export function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-xl bg-brand-gradient font-bold text-white shadow-glow"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
      aria-hidden="true"
    >
      D
    </span>
  );
}

export function BrandHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <BrandMark />
          <span className="leading-tight">
            <span className="block text-lg font-semibold tracking-tight text-white">DIVU AI</span>
            <span className="block text-[11px] uppercase tracking-[0.2em] text-brand-400">
              Beyond Conversations
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
          <span className="cursor-not-allowed text-slate-500" title="Phase 3">
            Chat
          </span>
          <span className="cursor-not-allowed text-slate-500" title="Phase 5">
            Agents
          </span>
          <span className="cursor-not-allowed text-slate-500" title="Phase 4">
            Knowledge
          </span>
          <span className="cursor-not-allowed text-slate-500" title="Phase 7">
            Studio
          </span>
          <span className="cursor-not-allowed text-slate-500" title="Phase 10">
            Admin
          </span>
        </nav>

        <div className="text-right leading-tight">
          <span className="block text-xs font-semibold tracking-wide text-slate-200">
            DIVYESH BAMBHANIYA
          </span>
          <span className="block text-[11px] text-slate-500">Founder &amp; Creator</span>
        </div>
      </div>
    </header>
  );
}
