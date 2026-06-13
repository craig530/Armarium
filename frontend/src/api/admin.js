import client from './client'

export const adminApi = {
  resetDatabase: () => client.post('/admin/reset-database').then((r) => r.data),
  redownloadCovers: () => client.post('/admin/covers/redownload-all').then((r) => r.data),
  purgeOrphanCovers: () => client.post('/admin/covers/purge-orphans').then((r) => r.data),
}
