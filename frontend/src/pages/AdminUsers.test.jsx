import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdminUsers from './AdminUsers'
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
    id: 1, username: 'admin', email: 'admin@example.com', is_admin: true, is_active: true, is_read_only: false,
    can_add_items: true, can_manage_locations: true, can_manage_platforms: true, can_manage_media_types: true,
    can_manage_lists: true, password_set: true, is_protected_super_admin: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2, username: 'alice', email: 'alice@example.com', is_admin: false, is_active: true, is_read_only: false,
    can_add_items: true, can_manage_locations: false, can_manage_platforms: false, can_manage_media_types: false,
    can_manage_lists: false, password_set: true, is_protected_super_admin: false,
    created_at: '2024-02-01T00:00:00Z',
  },
]

function renderAdminUsers() {
  return render(
    <MemoryRouter>
      <AdminUsers />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  client.get.mockResolvedValue({ data: mockUsers })
  client.post.mockResolvedValue({ data: {} })
  client.put.mockResolvedValue({ data: {} })
  client.delete.mockResolvedValue({ data: {} })
  useAuthStore.setState({ user: { username: 'admin', is_admin: true }, isAuthenticated: true })
  useReferenceDataStore.setState({ locations: [], platforms: [], mediaSubtypes: [], loaded: false, loading: null })
})

afterEach(() => {
  cleanup()
})

describe('AdminUsers', () => {
  it('renders the user list with role badges and a marker for the current user', async () => {
    renderAdminUsers()

    expect(await screen.findByText('alice')).toBeTruthy()
    const adminRow = screen.getByText('admin').closest('div')
    expect(within(adminRow).getByText('Admin')).toBeTruthy()
    expect(within(adminRow).getByText('(you)')).toBeTruthy()
  })

  it('shows validation errors for an invalid username and email', async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    fireEvent.click(screen.getByText('New user'))
    const form = screen.getByText('Create user').closest('form')
    fireEvent.change(within(form).getAllByRole('textbox')[0], { target: { value: 'a' } })
    fireEvent.change(form.querySelector('input[type="email"]'), { target: { value: 'not-an-email' } })
    fireEvent.click(within(form).getByText('Create'))

    expect(await screen.findByText('Use 3-50 characters: letters, numbers, underscores or hyphens only')).toBeTruthy()
    expect(screen.getByText('Enter a valid email address')).toBeTruthy()
    expect(client.post).not.toHaveBeenCalled()
  })

  it('creates a user (invite-only, no password field) and reloads the list', async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    fireEvent.click(screen.getByText('New user'))
    const form = screen.getByText('Create user').closest('form')
    expect(form.querySelector('input[type="password"]')).toBeNull()
    fireEvent.change(within(form).getAllByRole('textbox')[0], { target: { value: 'bob' } })
    fireEvent.change(form.querySelector('input[type="email"]'), { target: { value: 'bob@example.com' } })

    fireEvent.click(within(form).getByText('Create'))

    await waitFor(() => {
      expect(client.post).toHaveBeenCalledWith('/users', expect.objectContaining({ username: 'bob', email: 'bob@example.com' }))
    })
    await waitFor(() => {
      expect(screen.queryByText('Create user')).toBeNull()
    })
  })

  it('force-resets a user\'s password by emailing them a link, after confirming', async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    const aliceRow = screen.getByText('alice').closest('.py-3')
    fireEvent.click(within(aliceRow).getByTitle('Email a password-reset link'))

    fireEvent.click(await screen.findByText('Send reset link'))

    await waitFor(() => {
      expect(client.post).toHaveBeenCalledWith('/users/2/force-password-reset')
    })
  })

  it('disables force-password-reset for the protected super-admin account', async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    const adminRow = screen.getByText('admin').closest('.py-3')
    expect(within(adminRow).getByTitle("The default admin account's password is managed via .env").disabled).toBe(true)
  })

  it("toggles a non-admin user's admin role", async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    fireEvent.click(screen.getByTitle('Grant admin'))

    await waitFor(() => {
      expect(client.put).toHaveBeenCalledWith('/users/2', { is_admin: true })
    })
  })

  it('disables admin-toggle and delete for the current (self) admin user', async () => {
    renderAdminUsers()
    await screen.findByText('alice')

    expect(screen.getByTitle('Cannot change your own admin role').disabled).toBe(true)
    expect(screen.getByTitle('Cannot delete your own account').disabled).toBe(true)
  })
})
