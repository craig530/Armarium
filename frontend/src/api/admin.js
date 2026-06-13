import client from './client'

export const adminApi = {
  resetDatabase: () => client.post('/admin/reset-database').then((r) => r.data),
}
