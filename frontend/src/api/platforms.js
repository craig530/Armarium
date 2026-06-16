import client from './client'

export const platformsApi = {
  list: () => client.get('/platforms').then((r) => r.data),
  create: (data) => client.post('/platforms', data).then((r) => r.data),
  update: (id, data) => client.put(`/platforms/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/platforms/${id}`),
  moveItems: (id, toPlatformId) => client.post(`/platforms/${id}/move-items`, { to_platform_id: toPlatformId }).then((r) => r.data),
  uploadLogo: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post(`/platforms/${id}/logo`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}
