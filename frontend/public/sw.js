// Minimal service worker: precache the app shell, serve cached static assets,
// and always go to the network for the API (never cache live pet state).

const CACHE = 'picopals-v1'
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icons/icon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // Never intercept API calls.
  if (url.pathname.startsWith('/api/')) return

  // Network-first for navigations so deploys show up; fall back to cached shell.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/index.html'))
    )
    return
  }

  // Cache-first for other static assets.
  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((resp) => {
          const copy = resp.clone()
          if (resp.ok && url.origin === self.location.origin) {
            caches.open(CACHE).then((c) => c.put(event.request, copy))
          }
          return resp
        })
    )
  )
})
