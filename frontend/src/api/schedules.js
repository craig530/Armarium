import client from './client'

export const schedulesApi = {
  list: () => client.get('/admin/schedules').then((r) => r.data),
  get: (jobType) => client.get(`/admin/schedules/${jobType}`).then((r) => r.data),
  upsert: (jobType, data) => client.post(`/admin/schedules/${jobType}`, data).then((r) => r.data),
  delete: (jobType) => client.delete(`/admin/schedules/${jobType}`),
  runNow: (jobType) => client.post(`/admin/schedules/${jobType}/run-now`).then((r) => r.data),
}
