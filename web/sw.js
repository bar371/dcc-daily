/* Cache-first for the shell, network-first for the dataset.
   Bump CACHE when you change any shell file, or clients keep the old one. */
const CACHE = "dcc-daily-v3";
const SHELL = [
  ".", "index.html", "styles.css", "picker.js", "app.js",
  "entries-fallback.js", "manifest.webmanifest", "icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      // addAll rejects wholesale if any one file 404s; tolerate that.
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;  // let fonts hit the network

  // Dataset: try network so a refresh lands, fall back to cache offline.
  if (url.pathname.endsWith("entries.json")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((hit) => hit || fetch(request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(request, copy));
      return res;
    }))
  );
});
