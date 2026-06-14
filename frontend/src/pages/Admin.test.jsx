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
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2, username: 'alice', is_admin: false, is_active: true, is_read_only: false,
    can_add_items: true, can_manage_locations: false, can_manage_platforms: false, can_manage_media_types: false,
    created_at: '2024-02-01T00:00:00Z',
  },
]

function mockGet() {
  client.get.mockImplementation((url) => {
    if (url === '/users') return Promise.resolve({ data: mockUsers })
    if (url === '/library/backup/list') return Promise.resolve({ data: { backups: [], backup_supported: true } })
    if (url === '/admin/plex/config') {
      return Promise.resolve({ data: { configured: false, enabled: false, base_url: null, platform: null } })
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
  it('renders the user list with role badges and a marker for the current user', async () => {
    renderAdmin()

    expect(await screen.findByText('alice')).toBeTruthy()
    const adminRow = screen.getByText('admin').closest('div')
    expect(within(adminRow).getByText('Admin')).toBeTruthy()
    expect(within(adminRow).getByText('(you)')).toBeTruthy()
  })

  it('shows validation errors for an invalid username and short password', async () => {
    renderAdmin()
    await screen.findByText('alice')

    fireEvent.click(screen.getByText('New user'))
    const form = screen.getByText('Create user').closest('form')
    fireEvent.change(within(form).getByRole('textbox'), { target: { value: 'a' } })
    fireEvent.change(form.querySelector('input[type="password"]'), { target: { value: 'short' } })
    fireEvent.click(within(form).getByText('Create'))

    expect(await screen.findByText('Use 3-50 characters: letters, numbers, underscores or hyphens only')).toBeTruthy()
    expect(screen.getByText('Password must be at least 8 characters')).toBeTruthy()
    expect(client.post).not.toHaveBeenCalled()
  })

  it('creates a user and reloads the list', async () => {
    renderAdmin()
    await screen.findByText('alice')

    fireEvent.click(screen.getByText('New user'))
    const form = screen.getByText('Create user').closest('form')
    fireEvent.change(within(form).getByRole('textbox'), { target: { value: 'bob' } })
    fireEvent.change(form.querySelector('input[type="password"]'), { target: { value: 'longenoughpassword' } })

    fireEvent.click(within(form).getByText('Create'))

    await waitFor(() => {
      expect(client.post).toHaveBeenCalledWith('/users', expect.objectContaining({ username: 'bob', password: 'longenoughpassword' }))
    })
    await waitFor(() => {
      expect(screen.queryByText('Create user')).toBeNull()
    })
  })

  it("toggles a non-admin user's admin role", async () => {
    renderAdmin()
    await screen.findByText('alice')

    fireEvent.click(screen.getByTitle('Grant admin'))

    await waitFor(() => {
      expect(client.put).toHaveBeenCalledWith('/users/2', { is_admin: true })
    })
  })

  it('disables admin-toggle and delete for the current (self) admin user', async () => {
    renderAdmin()
    await screen.findByText('alice')

    expect(screen.getByTitle('Cannot change your own admin role').disabled).toBe(true)
    expect(screen.getByTitle('Cannot delete your own account').disabled).toBe(true)
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
