import client from './client'

export const lookupApi = {
  barcode: (barcode, mediaType) =>
    client.get(`/lookup/barcode/${barcode}`, { params: mediaType ? { media_type: mediaType } : {} }).then((r) => r.data),
  search: (q, mediaType, limit = 10) =>
    client.get('/lookup/search', { params: { q, media_type: mediaType, limit } }).then((r) => r.data),
  tmdbDetails: (tmdbId, mediaType) =>
    client.get(`/lookup/tmdb/${tmdbId}`, { params: { media_type: mediaType } }).then((r) => r.data),
}
