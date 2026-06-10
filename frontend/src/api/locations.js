import client from './client'

export const locationsApi = {
  list: () => client.get('/locations').then((r) => r.data),
  get: (id) => client.get(`/locations/${id}`).then((r) => r.data),
  create: (data) => client.post('/locations', data).then((r) => r.data),
  update: (id, data) => client.put(`/locations/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/locations/${id}`),
}
