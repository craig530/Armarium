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
    const msg = err.response?.data?.detail || err.message || 'An error occurred'
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  }
)

export default client
