/* DIVU AI service worker.
 *
 * Strategy:
 *   - App shell (/, /app, /offline, manifest, icons) is precached so the installed app opens
 *     instantly and renders even with no network.
 *   - Static assets (/_next/static/*) are served cache-first (they are content-hashed).
 *   - Navigations are network-first and fall back to the cached shell, then to /offline.html.
 *   - /api/* is network-only. Caching API responses would risk serving stale or wrong data to a
 *     signed-in user, and caching authenticated responses is a privacy hazard.
 *
 * Registered from the client only when NODE_ENV === 'production' (see ServiceWorkerRegistrar).
 */

const VERSION = "divu-ai-v1";
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;

const PRECACHE_URLS = [
  "/",
  "/app",
  "/download",
  "/offline.html",
  "/manifest.webmanifest",
  "/favicon.png",
  "/icons/icon-192.png",
  "/icons/icon-256.png",
  "/icons/icon-384.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png",
  "/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && response.type === "basic") {
    const cache = await caches.open(ASSET_CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    const offline = await caches.match("/offline.html");
    if (offline) return new Response(await offline.text(), {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
    return new Response("Offline", { status: 503, statusText: "Offline" });
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/health")) {
    // Live data only: never serve a stale API response from cache.
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(
            JSON.stringify({
              error: {
                code: "offline",
                message: "You are offline. Reconnect to reach the DIVU AI backend.",
              },
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            },
          ),
      ),
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request));
    return;
  }

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(cacheFirst(request));
    return;
  }

  event.respondWith(
    fetch(request).catch(() => caches.match(request).then((hit) => hit || Response.error())),
  );
});
