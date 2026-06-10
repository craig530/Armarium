const CACHE = 'armarium-v1'
const OFFLINE_URLS = ['/']

// Per-account identity/admin data — never persisted to Cache Storage.
const NO_CACHE_PATTERNS = [/^\/api\/v1\/auth\//, /^\/api\/v1\/users/]
const isCacheable = (pathname) => !NO_CACHE_PATTERNS.some((re) => re.test(pathname))

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(OFFLINE_URLS))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

// Let the page clear cached API responses on logout, so the next account to
// use this browser can't read the previous user's cached identity/admin data.
self.addEventListener('message', (e) => {
  if (e.data?.type === 'CLEAR_API_CACHE') {
    e.waitUntil(
      caches.open(CACHE).then(async (c) => {
        const requests = await c.keys()
        await Promise.all(
          requests
            .filter((req) => new URL(req.url).pathname.startsWith('/api/'))
            .map((req) => c.delete(req))
        )
      })
    )
  }
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)

  // Network-first for API (cache as fallback for offline browsing)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          if (res.ok && e.request.method === 'GET' && isCacheable(url.pathname)) {
            caches.open(CACHE).then((c) => c.put(e.request, res.clone()))
          }
          return res
        })
        .catch(() => caches.match(e.request))
    )
    return
  }

  // Cache-first for static assets; network-first for HTML
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() =>
        caches.match('/').then((r) => r || new Response('Offline', { status: 503 }))
      )
    )
    return
  }

  e.respondWith(
    caches.match(e.request).then((cached) =>
      cached ||
      fetch(e.request).then((res) => {
        if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, res.clone()))
        return res
      })
    )
  )
})
