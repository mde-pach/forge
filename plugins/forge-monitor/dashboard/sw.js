// Service worker for the forge sessions dashboard.
//
// Two caches, because the two things being cached have different truth. The
// shell (this file's neighbors: the page, the manifest, the icons) is only
// ever as fresh as the last deploy, so cache-first-then-refresh is correct
// and fast. The data (snapshot.json) is a live view of running sessions -
// serving a stale copy as if it were current would be worse than an error,
// so it is network-first and the cache is purely the fallback for when the
// network is the thing that's gone. That is the same "stale beats blank"
// rule index.html's own tick() already applies to a slow network; this is
// what makes it hold with no network at all, including on a cold start with
// no page open yet to hold state in a JS variable.

const SHELL_CACHE = "forge-dashboard-shell-v2"; // bumped: index.html now shows dirty_files
const DATA_CACHE = "forge-dashboard-data-v1";

const SHELL_FILES = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_FILES))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.filter((n) => n !== SHELL_CACHE && n !== DATA_CACHE).map((n) => caches.delete(n))
        )
      )
      .then(() => self.clients.claim())
  );
});

function isDataRequest(url) {
  return url.pathname.endsWith("/snapshot.json") || url.pathname.endsWith("/snapshot");
}

// Network-first: today's data beats yesterday's. Falls back to the last
// snapshot this device ever saw, so a phone that loses the connection shows
// the last thing it knew - greyed as stale by index.html's own age check,
// same as a slow store - instead of an error screen.
async function dataFirst(request) {
  const key = new Request(new URL(request.url).pathname); // drop the cache-busting ?t=
  try {
    const fresh = await fetch(request);
    if (fresh.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(key, fresh.clone());
      return fresh;
    }
    // The network answered, but not with data - today's server always
    // returns 200 and encodes staleness in the body, so this path is not
    // live yet. It stays "stale beats blank" regardless: fall back to the
    // last good snapshot if one exists, and only surface the real failure
    // response when there is nothing cached to fall back to.
    const cached = await caches.match(key);
    return cached || fresh;
  } catch (err) {
    const cached = await caches.match(key);
    if (cached) return cached;
    throw err;
  }
}

// Cache-first, refreshed in the background, so the next load has whatever
// changed. Falls back to the cached page itself for a navigation with no
// network and no matching entry - the one case a plain cache miss must not
// become a browser error page, since that is the "installed app opens to a
// blank screen offline" failure this whole file exists to prevent.
async function shellFirst(request) {
  const cached = await caches.match(request, { ignoreSearch: true });
  if (cached) {
    fetch(request)
      .then((res) => {
        if (res.ok) caches.open(SHELL_CACHE).then((c) => c.put(request, res.clone()));
      })
      .catch(() => {});
    return cached;
  }
  try {
    const fresh = await fetch(request);
    if (fresh.ok) {
      const cache = await caches.open(SHELL_CACHE);
      cache.put(request, fresh.clone());
    }
    return fresh;
  } catch (err) {
    if (request.mode === "navigate") {
      const shell = await caches.match("index.html");
      if (shell) return shell;
    }
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return; // nothing cross-origin is ever requested here
  if (event.request.method !== "GET") return;
  if (url.pathname.endsWith("/healthz")) return; // a liveness probe, never cached

  if (isDataRequest(url)) {
    event.respondWith(dataFirst(event.request));
  } else {
    event.respondWith(shellFirst(event.request));
  }
});
