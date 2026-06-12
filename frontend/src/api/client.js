import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('armarium-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Format a FastAPI error `detail` payload into a readable string.
// 422 validation errors arrive as a list of {loc, msg, ...} objects.
function formatErrorDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const field = Array.isArray(e?.loc) ? e.loc.filter((p) => p !== 'body').join('.') : null
        return field ? `${field}: ${e.msg}` : e?.msg
      })
      .filter(Boolean)
      .join('; ')
  }
  return JSON.stringify(detail)
}

// On 401, clear credentials and redirect to login
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('armarium-token')
      localStorage.removeItem('armarium-user')
      navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_API_CACHE' })
      window.location.href = '/login'
      return Promise.reject(new Error('Session expired. Please log in again.'))
    }
    const detail = err.response?.data?.detail
    const msg = detail != null ? formatErrorDetail(detail) : err.message || 'An error occurred'
    return Promise.reject(new Error(msg || 'An error occurred'))
  }
)

export default client
