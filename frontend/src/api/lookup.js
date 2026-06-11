import client from './client'

export const lookupApi = {
  barcode: (barcode, category) =>
    client.get(`/lookup/barcode/${barcode}`, { params: category ? { category } : {} }).then((r) => r.data),
  search: (q, category, limit = 10) =>
    client.get('/lookup/search', { params: { q, category, limit } }).then((r) => r.data),
  tmdbDetails: (tmdbId) =>
    client.get(`/lookup/tmdb/${tmdbId}`).then((r) => r.data),
}
