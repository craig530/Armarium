import client from './client'

export const plexApi = {
  getConfig: () => client.get('/admin/plex/config').then((r) => r.data),
  updateConfig: (data) => client.put('/admin/plex/config', data).then((r) => r.data),
  deleteConfig: () => client.delete('/admin/plex/config'),
  testConnection: (data) => client.post('/admin/plex/test', data).then((r) => r.data),

  getSections: () => client.get('/admin/plex/sections').then((r) => r.data),
  listMappings: () => client.get('/admin/plex/mappings').then((r) => r.data),
  createMapping: (data) => client.post('/admin/plex/mappings', data).then((r) => r.data),
  updateMapping: (id, data) => client.put(`/admin/plex/mappings/${id}`, data).then((r) => r.data),
  deleteMapping: (id) => client.delete(`/admin/plex/mappings/${id}`),
  // options: { auto_remove_stale: bool } — omit for default (false)
  syncMapping: (id, options) =>
    client.post(`/admin/plex/mappings/${id}/sync`, options ?? null).then((r) => r.data),
  getSyncStatus: (id) => client.get(`/admin/plex/mappings/${id}/sync/status`).then((r) => r.data),
  cancelSync: (id) => client.post(`/admin/plex/mappings/${id}/sync/cancel`).then((r) => r.data),
  removeStaleItems: (id, itemIds) =>
    client.post(`/admin/plex/mappings/${id}/remove-stale`, { item_ids: itemIds }).then((r) => r.data),

  getMappingSchedule: (id) =>
    client.get(`/admin/plex/mappings/${id}/schedule`).then((r) => r.data),
  upsertMappingSchedule: (id, data) =>
    client.post(`/admin/plex/mappings/${id}/schedule`, data).then((r) => r.data),
  deleteMappingSchedule: (id) =>
    client.delete(`/admin/plex/mappings/${id}/schedule`),
}
