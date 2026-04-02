const CACHE_NAME = "id-scan-demo-shell-v2";
const STATIC_ASSETS = [
  "/",
  "/admin",
  "/manifest.webmanifest",
  "/static/style.css",
  "/static/capture.js",
  "/static/admin.js",
  "/static/icon.svg",
];

function shouldHandle(request, url) {
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return false;
  }

  if (url.pathname.startsWith("/api/") || url.pathname === "/sw.js") {
    return false;
  }

  return true;
}

async function updateCache(request, response) {
  if (!response.ok) {
    return response;
  }

  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => updateCache(request, response))
    .catch(() => null);

  if (cached) {
    return cached;
  }

  const networkResponse = await networkPromise;
  if (networkResponse) {
    return networkResponse;
  }

  return caches.match("/");
}

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (!shouldHandle(request, url)) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => updateCache(request, response))
        .catch(() => caches.match(request).then((cached) => cached || caches.match("/")))
    );
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});
