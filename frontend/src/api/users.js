import client from './client'

export const usersApi = {
  summary: () => client.get('/users/summary').then((r) => r.data),
}
