import client from './client'

// Lookup-result cover thumbnails point straight at a third-party host
// (TMDB/Cover Art Archive/Open Library) — route them through the backend's
// cover-proxy so they load even when the client's network/DNS can't reach
// that host directly. Local/relative paths (e.g. already-saved `/covers/...`
// images) are left untouched.
export function coverProxyUrl(url) {
  if (!url || !/^https?:\/\//i.test(url)) return url
  return `/api/v1/lookup/cover-proxy?url=${encodeURIComponent(url)}`
}

export const lookupApi = {
  barcode: (barcode, category) =>
    client.get(`/lookup/barcode/${barcode}`, { params: category ? { category } : {} }).then((r) => r.data),
  search: (q, category, limit = 10, mediaKind = null) =>
    client.get('/lookup/search', { params: { q, category, limit, ...(mediaKind ? { media_kind: mediaKind } : {}) } }).then((r) => r.data),
  tmdbDetails: (tmdbId, mediaKind = null) =>
    client.get(`/lookup/tmdb/${tmdbId}`, { params: mediaKind ? { media_kind: mediaKind } : {} }).then((r) => r.data),
  // Sends a single camera frame (JPEG blob) to the server for barcode
  // decoding via zxing-cpp. `signal` lets the caller abort an in-flight
  // request (e.g. if the scanner closes before the response arrives).
  scan: (blob, signal) => {
    const form = new FormData()
    form.append('file', blob, 'frame.jpg')
    return client
      .post('/lookup/scan', form, { headers: { 'Content-Type': 'multipart/form-data' }, signal })
      .then((r) => r.data)
  },
}
