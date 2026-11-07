import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";

const LINKS = [
  { href: "/#platform", label: "Platform" },
  { href: "/#roadmap", label: "Roadmap" },
  { href: "/#security", label: "Security" },
  { href: "/download", label: "Install" },
];

export function BrandHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/85 backdrop-blur">
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
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="transition hover:text-white">
              {link.label}
            </Link>
          ))}
          <Link
            href="/app"
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 transition hover:bg-white/10"
          >
            Open workspace
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/app" className="btn-primary hidden px-3 py-1.5 text-xs sm:inline-flex">
            Launch app
          </Link>
          <div className="hidden text-right leading-tight lg:block">
            <span className="block text-xs font-semibold tracking-wide text-slate-200">
              DIVYESH BAMBHANIYA
            </span>
            <span className="block text-[11px] text-slate-500">Founder &amp; Creator</span>
          </div>
        </div>
      </div>
    </header>
  );
}
