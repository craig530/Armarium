import { create } from 'zustand'
import axios from 'axios'
import client from '../api/client'

// ── Theme ────────────────────────────────────────────────────────────────────

// Keeps the PWA status bar / browser chrome colour matching the navbar
// background (white in light mode, gray-950 in dark mode) so standalone mode
// doesn't show a mismatched bar above the header.
function applyThemeColor(dark) {
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#15100C' : '#FFFFFF')
}

export const useThemeStore = create((set) => {
  const initialDark = document.documentElement.classList.contains('dark')
  applyThemeColor(initialDark)

  return {
    dark: initialDark,
    toggle() {
      set((s) => {
        const next = !s.dark
        document.documentElement.classList.toggle('dark', next)
        localStorage.setItem('armarium-theme', next ? 'dark' : 'light')
        applyThemeColor(next)
        return { dark: next }
      })
    },
  }
})

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

// JWT payloads are base64url, not plain base64 — convert and pad before
// passing to atob, which otherwise throws on '-'/'_' or missing padding.
function decodeJwtPayload(token) {
  const base64url = token.split('.')[1]
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  return JSON.parse(atob(padded))
}

// Tell the service worker to drop any cached /api/ responses, so the next
// account to use this browser doesn't see the previous user's cached data.
function clearServiceWorkerCache() {
  navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_API_CACHE' })
}

// Mirrors the backend's require_permission() logic: admins bypass all
// checks, is_read_only overrides every can_* flag.
export function hasPermission(user, flag) {
  return !!user?.is_admin || (!user?.is_read_only && !!user?.[flag])
}

export const useAuthStore = create((set) => ({
  ...loadStoredAuth(),

  async login(username, password) {
    const resp = await axios.post('/api/v1/auth/login', { username, password })
    const { access_token } = resp.data
    const payload = decodeJwtPayload(access_token)
    const user = { username: payload.sub, is_admin: payload.is_admin }

    localStorage.setItem('armarium-token', access_token)
    localStorage.setItem('armarium-user', JSON.stringify(user))
    set({ token: access_token, user, isAuthenticated: true })

    // Populate the full profile (id + permission flags) from the API —
    // the JWT only carries username/is_admin.
    await useAuthStore.getState().refreshUser()
  },

  // Re-fetch the current user's profile (including permission flags) from
  // the API. Called after login and on app load so permissions stay fresh
  // without requiring re-login.
  async refreshUser() {
    try {
      const resp = await client.get('/auth/me')
      const user = resp.data
      localStorage.setItem('armarium-user', JSON.stringify(user))
      set({ user })
    } catch {
      // Token may be invalid/expired — the response interceptor handles 401s.
    }
  },

  logout() {
    localStorage.removeItem('armarium-token')
    localStorage.removeItem('armarium-user')
    set({ token: null, user: null, isAuthenticated: false })
    clearServiceWorkerCache()
  },
}))

// ── Library UI ───────────────────────────────────────────────────────────────

const DEFAULT_FILTERS = {
  q: '',
  supertype: '',
  media_subtype_id: '',
  platform_id: '',
  genre: '',
  year: '',
  location_id: '',
  sort: 'created_at',
  order: 'desc',
}

export const useLibraryStore = create((set) => ({
  viewMode: 'grid',
  filters: { ...DEFAULT_FILTERS },
  setViewMode: (mode) => set({ viewMode: mode }),
  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),
  resetFilters: () => set({ filters: { ...DEFAULT_FILTERS } }),
}))
