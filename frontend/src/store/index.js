import { create } from 'zustand'
import axios from 'axios'

// ── Theme ────────────────────────────────────────────────────────────────────

export const useThemeStore = create((set) => ({
  dark: document.documentElement.classList.contains('dark'),
  toggle() {
    set((s) => {
      const next = !s.dark
      document.documentElement.classList.toggle('dark', next)
      localStorage.setItem('armarium-theme', next ? 'dark' : 'light')
      return { dark: next }
    })
  },
}))

// ── Auth ─────────────────────────────────────────────────────────────────────

function loadStoredAuth() {
  try {
    const token = localStorage.getItem('armarium-token')
    const user = JSON.parse(localStorage.getItem('armarium-user') || 'null')
    return { token, user, isAuthenticated: !!token && !!user }
  } catch {
    return { token: null, user: null, isAuthenticated: false }
  }
}

export const useAuthStore = create((set) => ({
  ...loadStoredAuth(),

  async login(username, password) {
    const resp = await axios.post('/api/v1/auth/login', { username, password })
    const { access_token } = resp.data
    // Decode payload (JWT is not encrypted, just signed)
    const payload = JSON.parse(atob(access_token.split('.')[1]))
    const user = { username: payload.sub, is_admin: payload.is_admin }

    localStorage.setItem('armarium-token', access_token)
    localStorage.setItem('armarium-user', JSON.stringify(user))
    set({ token: access_token, user, isAuthenticated: true })
  },

  logout() {
    localStorage.removeItem('armarium-token')
    localStorage.removeItem('armarium-user')
    set({ token: null, user: null, isAuthenticated: false })
  },
}))

// ── Library UI ───────────────────────────────────────────────────────────────

export const useLibraryStore = create((set) => ({
  viewMode: 'grid',
  filters: {
    q: '',
    media_type: '',
    genre: '',
    year: '',
    location_id: '',
    sort: 'created_at',
    order: 'desc',
  },
  setViewMode: (mode) => set({ viewMode: mode }),
  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),
  resetFilters: () =>
    set({
      filters: { q: '', media_type: '', genre: '', year: '', location_id: '', sort: 'created_at', order: 'desc' },
    }),
}))
