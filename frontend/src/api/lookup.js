import client from './client'

export const lookupApi = {
  barcode: (barcode, category) =>
    client.get(`/lookup/barcode/${barcode}`, { params: category ? { category } : {} }).then((r) => r.data),
  search: (q, category, limit = 10, mediaKind = null) =>
    client.get('/lookup/search', { params: { q, category, limit, ...(mediaKind ? { media_kind: mediaKind } : {}) } }).then((r) => r.data),
  tmdbDetails: (tmdbId, mediaKind = null) =>
    client.get(`/lookup/tmdb/${tmdbId}`, { params: mediaKind ? { media_kind: mediaKind } : {} }).then((r) => r.data),
}
