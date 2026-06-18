import client from './client'

export const usersApi = {
  summary: () => client.get('/users/summary').then((r) => r.data),
  update: (id, data) => client.put(`/users/${id}`, data).then((r) => r.data),
}
