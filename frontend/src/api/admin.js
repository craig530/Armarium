import client from './client'

export const adminApi = {
  resetDatabase: () => client.post('/admin/reset-database').then((r) => r.data),
  redownloadCovers: () => client.post('/admin/covers/redownload-all').then((r) => r.data),
  purgeOrphanCovers: () => client.post('/admin/covers/purge-orphans').then((r) => r.data),
  autoLink: () => client.post('/admin/auto-link').then((r) => r.data),
  systemInfo: () => client.get('/admin/system-info').then((r) => r.data),
}
