import client from './client'

export const listsApi = {
  list: (params) => client.get('/lists', { params }).then((r) => r.data),
  create: (data) => client.post('/lists', data).then((r) => r.data),
  update: (id, data) => client.put(`/lists/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/lists/${id}`),
}
