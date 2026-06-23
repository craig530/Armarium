import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, Shield, ShieldOff, Check, X, RefreshCw, Pencil, ArrowLeft, Mail } from 'lucide-react'
import client from '../api/client'
import { usersApi } from '../api/users'
import { useAuthStore, useReferenceDataStore } from '../store'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { useConfirm } from '../hooks/useConfirm'
import toast from 'react-hot-toast'

const USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,50}$/
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const PERMISSION_FLAGS = [
  { key: 'can_add_items', label: 'Add items' },
  { key: 'can_manage_locations', label: 'Manage locations' },
  { key: 'can_manage_platforms', label: 'Manage platforms' },
  { key: 'can_manage_media_types', label: 'Manage mediums' },
  { key: 'can_manage_lists', label: 'Manage lists' },
  { key: 'can_manage_schedules', label: 'Manage Plex sync schedules' },
]

const EMPTY_FORM = {
  username: '',
  display_name: '',
  email: '',
  is_admin: false,
  is_read_only: false,
  can_add_items: true,
  can_manage_locations: true,
  can_manage_platforms: true,
  can_manage_media_types: false,
  can_manage_lists: true,
  can_manage_schedules: true,
}

function PermissionToggles({ value, onChange }) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
        <input
          type="checkbox"
          checked={value.is_read_only}
          onChange={(e) => onChange('is_read_only', e.target.checked)}
          className="rounded-sm"
        />
        Read only (overrides all permissions below)
      </label>
      {PERMISSION_FLAGS.map(({ key, label }) => (
        <label
          key={key}
          className={`flex items-center gap-2 text-sm cursor-pointer ${
            value.is_read_only ? 'text-gray-400 dark:text-gray-600' : 'text-gray-700 dark:text-gray-300'
          }`}
        >
          <input
            type="checkbox"
            checked={value[key]}
            disabled={value.is_read_only}
            onChange={(e) => onChange(key, e.target.checked)}
            className="rounded-sm"
          />
          {label}
        </label>
      ))}
    </div>
  )
}

function UserRow({ user, currentUserId, adminCount, onUpdated, onDeleted }) {
  const [editMode, setEditMode] = useState(null) // null | 'display_name' | 'email'
  const [newDisplayName, setNewDisplayName] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const isSelf = user.id === currentUserId
  const isLastAdmin = user.is_admin && adminCount <= 1

  const handleToggleAdmin = async () => {
    try {
      await client.put(`/users/${user.id}`, { is_admin: !user.is_admin })
      toast.success(user.is_admin ? 'Admin role removed' : 'Admin role granted')
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleToggleActive = async () => {
    try {
      await client.put(`/users/${user.id}`, { is_active: !user.is_active })
      toast.success(user.is_active ? 'User deactivated' : 'User activated')
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleTogglePermission = async (key, checked) => {
    try {
      await client.put(`/users/${user.id}`, { [key]: checked })
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleForceReset = async () => {
    if (!await confirm(
      `Send ${user.username} a link to set a new password? Their current password stops working immediately.`,
      { title: 'Reset password?', confirmLabel: 'Send reset link' }
    )) return
    setSaving(true)
    try {
      await usersApi.forcePasswordReset(user.id)
      toast.success(`Password reset email sent to ${user.email}`)
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleEmailSave = async () => {
    if (!newEmail.trim()) return
    setSaving(true)
    try {
      await client.put(`/users/${user.id}`, { email: newEmail.trim() })
      toast.success('Email updated')
      setEditMode(null)
      setNewEmail('')
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDisplayNameSave = async () => {
    setSaving(true)
    try {
      await client.put(`/users/${user.id}`, { display_name: newDisplayName.trim() || null })
      toast.success('Display name updated')
      setEditMode(null)
      setNewDisplayName('')
      onUpdated()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!await confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    try {
      await client.delete(`/users/${user.id}`)
      toast.success('User deleted')
      onDeleted(user.id)
    } catch (err) {
      toast.error(err.message)
    }
  }

  const displayLabel = user.display_name || user.username

  return (
    <div className="py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-gray-900 dark:text-white">{displayLabel}</span>
            {user.display_name && (
              <span className="text-xs text-gray-400">@{user.username}</span>
            )}
            {user.is_admin && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                Admin
              </span>
            )}
            {!user.is_active && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/40">
                Inactive
              </span>
            )}
            {!user.password_set && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                Invited — pending
              </span>
            )}
            {isSelf && (
              <span className="text-xs text-gray-400">(you)</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Added {new Date(user.created_at).toLocaleDateString()}
          </p>
          {editMode === 'email' ? (
            <div className="flex items-center gap-2 mt-1">
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder={user.email || 'Email'}
                className="flex-1 sm:flex-none sm:w-48 text-base sm:text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                autoFocus
              />
              <button onClick={handleEmailSave} disabled={saving} className="p-1 rounded-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 shrink-0">
                <Check size={14} />
              </button>
              <button onClick={() => { setEditMode(null); setNewEmail('') }} className="p-1 rounded-sm text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 shrink-0">
                <X size={14} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setEditMode('email'); setNewEmail(user.email || '') }}
              className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-brand-600 mt-0.5"
            >
              <Mail size={11} /> {user.email || 'No email on file'}
            </button>
          )}
        </div>

        {/* Inline edit panel for display name */}
        {editMode === 'display_name' ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder={user.display_name || 'Display name'}
              maxLength={100}
              className="flex-1 sm:flex-none sm:w-36 text-base sm:text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              autoFocus
            />
            <button onClick={handleDisplayNameSave} disabled={saving} className="p-1 rounded-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 shrink-0">
              <Check size={14} />
            </button>
            <button onClick={() => { setEditMode(null); setNewDisplayName('') }} className="p-1 rounded-sm text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 shrink-0">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1 self-end sm:self-auto">
            <button
              onClick={() => { setEditMode('display_name'); setNewDisplayName(user.display_name || '') }}
              title="Edit display name"
              className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Pencil size={14} />
            </button>
            <button
              onClick={handleForceReset}
              disabled={user.is_protected_super_admin || !user.email}
              title={
                user.is_protected_super_admin ? "The default admin account's password is managed via .env"
                  : !user.email ? 'Add an email first'
                    : 'Email a password-reset link'
              }
              className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"
            >
              <RefreshCw size={14} />
            </button>
            <button
              onClick={handleToggleAdmin}
              disabled={isSelf || isLastAdmin}
              title={
                isSelf ? 'Cannot change your own admin role'
                  : isLastAdmin ? 'Cannot remove the last administrator'
                    : user.is_admin ? 'Remove admin' : 'Grant admin'
              }
              className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"
            >
              {user.is_admin ? <ShieldOff size={14} /> : <Shield size={14} />}
            </button>
            <button
              onClick={handleToggleActive}
              disabled={isSelf || (isLastAdmin && user.is_active)}
              title={
                isSelf ? 'Cannot deactivate your own account'
                  : (isLastAdmin && user.is_active) ? 'Cannot deactivate the last administrator'
                    : user.is_active ? 'Deactivate' : 'Activate'
              }
              className="p-1.5 rounded-lg text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-30"
            >
              {user.is_active ? <X size={14} /> : <Check size={14} />}
            </button>
            <button
              onClick={handleDelete}
              disabled={isSelf || isLastAdmin}
              title={
                isSelf ? 'Cannot delete your own account'
                  : isLastAdmin ? 'Cannot delete the last administrator'
                    : 'Delete user'
              }
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Permission flags (admins always have full access) */}
      {!user.is_admin && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
          <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={user.is_read_only}
              onChange={(e) => handleTogglePermission('is_read_only', e.target.checked)}
              className="rounded-sm"
            />
            Read only
          </label>
          {PERMISSION_FLAGS.map(({ key, label }) => (
            <label
              key={key}
              className={`flex items-center gap-1.5 text-xs cursor-pointer ${
                user.is_read_only ? 'text-gray-400 dark:text-gray-600' : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              <input
                type="checkbox"
                checked={user[key]}
                disabled={user.is_read_only}
                onChange={(e) => handleTogglePermission(key, e.target.checked)}
                className="rounded-sm"
              />
              {label}
            </label>
          ))}
        </div>
      )}

      {confirmDialog}
    </div>
  )
}

export default function AdminUsers() {
  const { user: currentUser } = useAuthStore()
  const { invalidate: invalidateRefData } = useReferenceDataStore()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [formErrors, setFormErrors] = useState({})
  const [creating, setCreating] = useState(false)

  const load = () => {
    setLoading(true)
    client.get('/users').then((r) => setUsers(r.data)).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()

    const errors = {}
    if (!USERNAME_PATTERN.test(form.username)) {
      errors.username = 'Use 3-50 characters: letters, numbers, underscores or hyphens only'
    }
    if (!EMAIL_PATTERN.test(form.email)) {
      errors.email = 'Enter a valid email address'
    }
    setFormErrors(errors)
    if (Object.keys(errors).length > 0) return

    setCreating(true)
    try {
      await client.post('/users', { ...form, display_name: form.display_name.trim() || undefined })
      toast.success(`User "${form.username}" created — they'll get an email to set their password`)
      setShowForm(false)
      setForm({ ...EMPTY_FORM })
      setFormErrors({})
      load()
      // Refresh the reference data store so owner dropdowns on item pages
      // pick up the new user without requiring a full page reload.
      invalidateRefData()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setCreating(false)
    }
  }

  // Find current user's ID from the list (we need the DB id, not from the token)
  const currentDbUser = users.find((u) => u.username === currentUser?.username)
  const adminCount = users.filter((u) => u.is_admin).length

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <Link to="/admin" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white mb-3">
          <ArrowLeft size={14} /> Admin
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Users</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage accounts, roles, and permissions</p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">{users.length} user{users.length === 1 ? '' : 's'}</h2>
          <Button size="sm" onClick={() => setShowForm((s) => !s)}>
            <Plus size={14} /> New user
          </Button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} noValidate className="mb-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 space-y-3">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">Create user</h3>
            <Input
              label="Username"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              error={formErrors.username}
              autoFocus
            />
            <Input
              label="Display name (optional)"
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              placeholder="Shown in ownership labels, defaults to username"
            />
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              error={formErrors.email}
              placeholder="They'll get a link to this address to set their password"
            />
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => setForm((f) => ({ ...f, is_admin: e.target.checked }))}
                className="rounded-sm"
              />
              Grant admin role
            </label>
            {!form.is_admin && (
              <PermissionToggles
                value={form}
                onChange={(key, checked) => setForm((f) => ({ ...f, [key]: checked }))}
              />
            )}
            <div className="flex gap-2">
              <Button size="sm" type="submit" loading={creating}>Create</Button>
              <Button size="sm" variant="ghost" type="button" onClick={() => { setShowForm(false); setFormErrors({}) }}>Cancel</Button>
            </div>
          </form>
        )}

        {loading ? (
          <p className="text-sm text-gray-400 animate-pulse">Loading users…</p>
        ) : (
          <div>
            {users.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                currentUserId={currentDbUser?.id}
                adminCount={adminCount}
                onUpdated={load}
                onDeleted={(id) => setUsers((us) => us.filter((u) => u.id !== id))}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
