import client from './client'

export const mediaApi = {
  list: (params) => client.get('/media', { params }).then((r) => r.data),
  get: (id) => client.get(`/media/${id}`).then((r) => r.data),
  create: (data) => client.post('/media', data).then((r) => r.data),
  update: (id, data) => client.put(`/media/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/media/${id}`),
  stats: () => client.get('/media/stats').then((r) => r.data),
  uploadCover: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post(`/media/${id}/cover`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}
