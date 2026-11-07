"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { UserResponse } from "@/lib/api";

type Mode = "login" | "register";

export function AuthPanel({ onAuthChange }: { onAuthChange?: (user: UserResponse | null) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [user, setUser] = useState<UserResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const notify = (next: UserResponse | null) => {
    setUser(next);
    onAuthChange?.(next);
  };

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "register") {
        const created = await api.register(email, password, fullName);
        notify(null);
        setNotice(`Account created for ${created.email}. You can sign in now.`);
        setMode("login");
      } else {
        await api.login(email, password);
        const me = await api.me();
        notify(me);
      }
      setPassword("");
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}${
              caught.details ? ` (${JSON.stringify(caught.details)})` : ""
            }`
          : caught instanceof Error
            ? caught.message
            : "Request failed";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await api.logout();
      notify(null);
      setNotice("Signed out and the refresh token was revoked.");
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h2 className="text-base font-semibold text-white">Signed in</h2>
          <span className={user.is_superuser ? "badge-warn" : "badge-ok"}>
            {user.is_superuser ? "superuser" : "authenticated"}
          </span>
        </div>
        <div className="space-y-3 p-5">
          <dl>
            <div className="kv">
              <dt className="kv-key">Email</dt>
              <dd className="kv-value">{user.email}</dd>
            </div>
            <div className="kv">
              <dt className="kv-key">Name</dt>
              <dd className="kv-value">{user.full_name || "—"}</dd>
            </div>
            <div className="kv">
              <dt className="kv-key">Roles</dt>
              <dd className="kv-value">{user.roles.join(", ") || "—"}</dd>
            </div>
          </dl>
          <button type="button" className="btn-ghost" onClick={() => void logout()} disabled={busy}>
            Sign out
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="text-base font-semibold text-white">
          {mode === "login" ? "Sign in" : "Create account"}
        </h2>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
            setNotice(null);
          }}
        >
          {mode === "login" ? "Need an account?" : "Have an account?"}
        </button>
      </div>

      <form className="space-y-3 p-5" onSubmit={submit}>
        {mode === "register" && (
          <label className="block">
            <span className="mb-1 block text-xs text-slate-400">Full name</span>
            <input
              className="field"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Divyesh Bambhaniya"
              autoComplete="name"
            />
          </label>
        )}
        <label className="block">
          <span className="mb-1 block text-xs text-slate-400">Email</span>
          <input
            className="field"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@divu.ai"
            autoComplete="email"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-400">Password</span>
          <input
            className="field"
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 12 characters"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>

        {error && (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            {error}
          </p>
        )}
        {notice && (
          <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
            {notice}
          </p>
        )}

        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </section>
  );
}
