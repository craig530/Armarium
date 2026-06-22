import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Admin from './Admin'
import client from '../api/client'
import { useAuthStore, useReferenceDataStore } from '../store'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockUsers = [
  {
    id: 1, username: 'admin', is_admin: true, is_active: true, is_read_only: false,
    can_add_items: true, can_manage_locations: true, can_manage_platforms: true, can_manage_media_types: true,
    can_manage_lists: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2, username: 'alice', is_admin: false, is_active: true, is_read_only: false,
    can_add_items: true, can_manage_locations: false, can_manage_platforms: false, can_manage_media_types: false,
    can_manage_lists: false,
    created_at: '2024-02-01T00:00:00Z',
  },
]

function mockGet() {
  client.get.mockImplementation((url) => {
    if (url === '/users') return Promise.resolve({ data: mockUsers })
    if (url === '/users/summary') return Promise.resolve({ data: mockUsers })
    if (url === '/library/backup/list') return Promise.resolve({ data: { backups: [], backup_supported: true } })
    if (url === '/admin/plex/config') {
      return Promise.resolve({ data: { configured: false, enabled: false, base_url: null, platform: null } })
    }
    if (url === '/admin/system-info') {
      return Promise.resolve({
        data: {
          version: '1.7.0', database: 'SQLite', cors_origins: '*', configured_port: '8080',
          apis: { tmdb: false, igdb: false, upcdatabase: false },
        },
      })
    }
    return Promise.resolve({ data: [] })
  })
}

function renderAdmin() {
  return render(
    <MemoryRouter>
      <Admin />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGet()
  client.post.mockResolvedValue({ data: {} })
  client.put.mockResolvedValue({ data: {} })
  client.delete.mockResolvedValue({ data: {} })
  useAuthStore.setState({ user: { username: 'admin', is_admin: true }, isAuthenticated: true })
  useReferenceDataStore.setState({ locations: [], platforms: [], mediaSubtypes: [], loaded: false, loading: null })
})

afterEach(() => {
  cleanup()
})

describe('Admin', () => {
  it('shows a Users summary card linking to the dedicated users page', async () => {
    renderAdmin()

    const link = await screen.findByRole('link', { name: /users/i })
    expect(link.getAttribute('href')).toBe('/admin/users')
    expect(within(link).getByText('2 users')).toBeTruthy()
  })

  it('shows the empty backups state and triggers a backup', async () => {
    renderAdmin()

    await screen.findByText('No backups yet. Click "Backup now" to create one.')

    client.post.mockResolvedValue({ data: { backup: 'armarium-20260610.db' } })
    fireEvent.click(screen.getByText('Backup now'))

    await waitFor(() => {
      expect(client.post).toHaveBeenCalledWith('/library/backup')
    })
  })
})
