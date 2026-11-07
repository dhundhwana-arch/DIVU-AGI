"use client";

import { useEffect, useState } from "react";

/**
 * Registers the service worker that makes DIVU AI installable as a home-screen app.
 *
 * Registration is limited to production builds: in `next dev` the service worker would cache
 * hot-reload chunks and serve stale code.
 */
export function ServiceWorkerRegistrar() {
  const [status, setStatus] = useState<"idle" | "registered" | "unsupported" | "failed">("idle");

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) {
      setStatus("unsupported");
      return;
    }

    let cancelled = false;
    navigator.serviceWorker
      .register("/sw.js", { scope: "/", updateViaCache: "none" })
      .then((registration) => {
        if (cancelled) return;
        setStatus("registered");
        registration.addEventListener("updatefound", () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.addEventListener("statechange", () => {
            if (installing.state === "installed" && navigator.serviceWorker.controller) {
              // A new version is ready; it activates on the next navigation.
              setStatus("registered");
            }
          });
        });
      })
      .catch(() => {
        if (!cancelled) setStatus("failed");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (process.env.NODE_ENV !== "production" || status === "idle") return null;
  return null;
}
