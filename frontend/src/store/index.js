import { create } from 'zustand'
import axios from 'axios'
import client from '../api/client'
import { locationsApi } from '../api/locations'
import { platformsApi } from '../api/platforms'
import { mediaSubtypesApi } from '../api/mediaSubtypes'
import { listsApi } from '../api/lists'

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

// Follow OS theme changes live while the app is open, but only if the user
// hasn't manually overridden the theme (no 'armarium-theme' in localStorage).
// Re-checks localStorage inside the handler in case toggle() set an override
// mid-session, after this listener was registered. matchMedia is unavailable
// in the jsdom test environment, hence the guard.
if (typeof window.matchMedia === 'function') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (localStorage.getItem('armarium-theme')) return
    const next = e.matches
    document.documentElement.classList.toggle('dark', next)
    applyThemeColor(next)
    useThemeStore.setState({ dark: next })
  })
}

// ── Auth ─────────────────────────────────────────────────────────────────────

// The JWT itself lives in an httpOnly cookie set by the server, so the
// frontend never sees the token — only this cached (non-secret) user object,
// used for an optimistic initial render before refreshUser() confirms the
// cookie is still valid.
function loadStoredAuth() {
  try {
    const user = JSON.parse(localStorage.getItem('armarium-user') || 'null')
    return { user, isAuthenticated: !!user }
  } catch {
    return { user: null, isAuthenticated: false }
  }
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
    // Sets the httpOnly access-token cookie via Set-Cookie; the response
    // body's access_token is for API clients (see README), not used here.
    await axios.post('/api/v1/auth/login', { username, password })

    // Populate the full profile (id + permission flags) from the API.
    await useAuthStore.getState().refreshUser()
  },

  // Re-fetch the current user's profile (including permission flags) from
  // the API. Called after login and on app load so permissions stay fresh
  // without requiring re-login, and to confirm the access-token cookie is
  // still valid.
  async refreshUser() {
    try {
      const resp = await client.get('/auth/me')
      const user = resp.data
      localStorage.setItem('armarium-user', JSON.stringify(user))
      set({ user, isAuthenticated: true })
    } catch {
      // Cookie missing/expired — the response interceptor handles the
      // redirect to /login; clear the cached user so isAuthenticated
      // reflects reality on the next render.
      localStorage.removeItem('armarium-user')
      set({ user: null, isAuthenticated: false })
    }
  },

  async logout() {
    try {
      await client.post('/auth/logout')
    } catch {
      // Best effort — clear local state regardless.
    }
    localStorage.removeItem('armarium-user')
    set({ user: null, isAuthenticated: false })
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
  list_id: '',
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

// ── Reference data (locations / platforms / media subtypes) ────────────────
//
// Shared, lazily-loaded cache for the small lookup lists used across
// Library, Home, ItemDetail and the Add flow. Avoids re-fetching all three
// lists on every page/category switch; call `invalidate()` after any
// create/update/delete in the Settings managers so the next `ensureLoaded()`
// picks up the change.

export const useReferenceDataStore = create((set, get) => ({
  locations: [],
  platforms: [],
  mediaSubtypes: [],
  lists: [],
  loaded: false,
  loading: null,
  ensureLoaded() {
    if (get().loaded || get().loading) return get().loading
    const promise = Promise.all([locationsApi.list(), platformsApi.list(), mediaSubtypesApi.list(), listsApi.list()])
      .then(([locations, platforms, mediaSubtypes, lists]) => {
        set({ locations, platforms, mediaSubtypes, lists, loaded: true, loading: null })
      })
      .catch(() => set({ loading: null }))
    set({ loading: promise })
    return promise
  },
  invalidate() {
    set({ loaded: false })
  },
}))
