import client from './client'

export const plexApi = {
  getConfig: () => client.get('/admin/plex/config').then((r) => r.data),
  updateConfig: (data) => client.put('/admin/plex/config', data).then((r) => r.data),
  deleteConfig: () => client.delete('/admin/plex/config'),
  testConnection: (data) => client.post('/admin/plex/test', data).then((r) => r.data),
}
