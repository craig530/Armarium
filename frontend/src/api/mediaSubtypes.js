import client from './client'

export const mediaSubtypesApi = {
  list: (params) => client.get('/media-subtypes', { params }).then((r) => r.data),
  create: (data) => client.post('/media-subtypes', data).then((r) => r.data),
  update: (id, data) => client.put(`/media-subtypes/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/media-subtypes/${id}`),
}
