import { create } from 'zustand'
import axios from 'axios'
import client from '../api/client'
import { locationsApi } from '../api/locations'
import { platformsApi } from '../api/platforms'
import { mediaSubtypesApi } from '../api/mediaSubtypes'
import { listsApi } from '../api/lists'
import { plexApi } from '../api/plex'
import { usersApi } from '../api/users'
import { appConfigApi } from '../api/appConfig'

// ── Theme ────────────────────────────────────────────────────────────────────

// Keeps the PWA status bar / browser chrome colour matching the navbar
// background (white in light mode, gray-950 in dark mode) so standalone mode
// doesn't show a mismatched bar above the header.
function applyThemeColor(dark) {
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#15100C' : '#FFFFFF')
}

function applyDark(dark) {
  document.documentElement.classList.toggle('dark', dark)
  applyThemeColor(dark)
}

// Resolve whether dark mode should be active given a preference and the OS setting.
function resolveIsDark(preference, osDark) {
  if (preference === 'dark') return true
  if (preference === 'light') return false
  return osDark  // 'auto'
}

export const useThemeStore = create((set, get) => {
  const initialDark = document.documentElement.classList.contains('dark')
  applyThemeColor(initialDark)

  return {
    dark: initialDark,
    // 'auto' | 'light' | 'dark' — persisted to localStorage and (when logged in) to the user profile.
    preference: (() => { try { return localStorage.getItem('armarium-theme-pref') || 'auto' } catch { return 'auto' } })(),

    // Apply a new preference locally. Call savePreference() to also persist to the backend.
    setPreference(pref) {
      const osDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
      const dark = resolveIsDark(pref, osDark)
      try { localStorage.setItem('armarium-theme-pref', pref) } catch { /* no-op in test env */ }
      applyDark(dark)
      set({ preference: pref, dark })
    },

    // Legacy toggle — cycles through light → dark → auto. Used by the
    // mobile Profile page toggle button.
    toggle() {
      const { preference, setPreference } = get()
      const next = preference === 'light' ? 'dark' : preference === 'dark' ? 'auto' : 'light'
      setPreference(next)
    },
  }
})

// Follow OS theme changes live while the app is open, but only if the user's
// preference is 'auto'. matchMedia is unavailable in the jsdom test environment.
if (typeof window.matchMedia === 'function') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const { preference } = useThemeStore.getState()
    if (preference !== 'auto') return
    const dark = e.matches
    applyDark(dark)
    useThemeStore.setState({ dark })
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
      // Apply the user's stored theme preference (if any).
      if (user.theme_preference) {
        useThemeStore.getState().setPreference(user.theme_preference)
      }
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
  owner_id: '',
  rating: '',
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

// ── Library stats (category totals) ──────────────────────────────────────────
// Populated by Layout on every navigation; read by Library and Home to show
// item counts alongside category headings without an extra per-page fetch.
export const useStatsStore = create((set) => ({
  stats: null,
  setStats: (stats) => set({ stats }),
}))

// ── Reference data (locations / platforms / media subtypes) ────────────────
//
// Shared, lazily-loaded cache for the small lookup lists used across
// Library, Home, ItemDetail and the Add flow. Avoids re-fetching all three
// lists on every page/category switch; call `invalidate()` after any
// create/update/delete in the Settings managers so the next `ensureLoaded()`
// picks up the change.
//
// appConfig is persisted to localStorage so the initial render knows which
// categories are disabled without waiting for the API response (prevents the
// flash of disabled categories on load).

function loadStoredAppConfig() {
  try {
    return JSON.parse(localStorage.getItem('armarium-appconfig') || 'null')
  } catch {
    return null
  }
}

export const useReferenceDataStore = create((set, get) => ({
  locations: [],
  platforms: [],
  mediaSubtypes: [],
  lists: [],
  users: [],
  appConfig: loadStoredAppConfig(),
  plexStatus: null,
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
    // These load independently so they never block the main reference data or
    // hang tests that only mock the core four APIs.
    plexApi.getStatus()
      .then((plexStatus) => set({ plexStatus }))
      .catch(() => {})
    usersApi.summary()
      .then((users) => set({ users }))
      .catch(() => {})
    appConfigApi.get()
      .then((appConfig) => {
        try { localStorage.setItem('armarium-appconfig', JSON.stringify(appConfig)) } catch { /* no-op in test env */ }
        set({ appConfig })
      })
      .catch(() => {})
    return promise
  },
  // Directly update appConfig in the store and persist to localStorage.
  // Use this after admin saves to avoid clearing and re-fetching everything.
  setAppConfig(appConfig) {
    try { localStorage.setItem('armarium-appconfig', JSON.stringify(appConfig)) } catch { /* no-op in test env */ }
    set({ appConfig })
  },
  invalidate() {
    set({ loaded: false, plexStatus: null, users: [], appConfig: null })
    try { localStorage.removeItem('armarium-appconfig') } catch { /* no-op in test env */ }
  },
}))
