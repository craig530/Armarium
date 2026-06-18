import client from './client'

export const appConfigApi = {
  get: () => client.get('/admin/config').then((r) => r.data),
  update: (data) => client.put('/admin/config', data).then((r) => r.data),
  migrateOwnership: (data) => client.post('/admin/config/migrate-ownership', data).then((r) => r.data),
}
