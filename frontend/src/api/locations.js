import client from './client'

export const locationsApi = {
  list: () => client.get('/locations').then((r) => r.data),
  get: (id) => client.get(`/locations/${id}`).then((r) => r.data),
  create: (data) => client.post('/locations', data).then((r) => r.data),
  update: (id, data) => client.put(`/locations/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/locations/${id}`),
  moveItems: (id, toLocationId) => client.post(`/locations/${id}/move-items`, { to_location_id: toLocationId }).then((r) => r.data),
  uploadIcon: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post(`/locations/${id}/icon`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}
