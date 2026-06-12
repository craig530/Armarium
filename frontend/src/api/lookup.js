import client from './client'

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
