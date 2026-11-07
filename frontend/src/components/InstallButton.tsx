"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

type Platform = "unknown" | "ios" | "android" | "desktop";

function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent;
  const iOS = /iphone|ipad|ipod/i.test(ua) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(ua));
  if (iOS) return "ios";
  if (/android/i.test(ua)) return "android";
  return "desktop";
}

/**
 * Installs DIVU AI to the home screen.
 *
 * Chromium/Android/Windows expose `beforeinstallprompt`, which we capture and fire on click.
 * iOS Safari does not, so we show the exact manual steps instead of pretending a button works.
 */
export function InstallButton({ className = "btn-primary" }: { className?: string }) {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [showIosHelp, setShowIosHelp] = useState(false);
  const [platform, setPlatform] = useState<Platform>("unknown");

  useEffect(() => {
    setPlatform(detectPlatform());
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => setInstalled(true);

    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);

    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (window.navigator as { standalone?: boolean }).standalone === true;
    if (isStandalone) setInstalled(true);

    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    if (!deferred) {
      setShowIosHelp(true);
      return;
    }
    await deferred.prompt();
    const choice = await deferred.userChoice;
    if (choice.outcome === "accepted") setInstalled(true);
    setDeferred(null);
  }

  if (installed) {
    return (
      <span className="badge-ok" title="DIVU AI is installed on this device">
        Installed
      </span>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button type="button" className={className} onClick={() => void install()}>
        {deferred ? "Install DIVU AI" : "Add to home screen"}
      </button>

      {showIosHelp && (
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-xs text-slate-300">
          {platform === "ios" ? (
            <ol className="ml-4 list-decimal space-y-1">
              <li>
                Tap the <strong>Share</strong> button in Safari.
              </li>
              <li>
                Choose <strong>Add to Home Screen</strong>.
              </li>
              <li>
                Confirm — DIVU AI appears as an app icon and opens full screen.
              </li>
            </ol>
          ) : (
            <p>
              Use your browser menu: <strong>Install app</strong> / <strong>Add to Home screen</strong>
              {platform === "android" ? " (Chrome → ⋮ → Install app)" : " (Chrome → ⋮ → Cast, save & share → Install)"}
              . It runs offline for the app shell and reconnects to the backend automatically.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
