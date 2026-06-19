import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { Plus, Trash2, Shield, ShieldOff, Check, X, RefreshCw, AlertTriangle, Download, Link2, Pencil, Users, Info } from 'lucide-react'
import client from '../api/client'
import { adminApi } from '../api/admin'
import { plexApi } from '../api/plex'
import { schedulesApi } from '../api/schedules'
import { appConfigApi } from '../api/appConfig'
import { usersApi } from '../api/users'
import { exportCovers } from '../lib/export'
import { useAuthStore, useReferenceDataStore, useStatsStore } from '../store'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import SelectMenu from '../components/ui/SelectMenu'
import PlatformLogo from '../components/ui/PlatformLogo'
import ScheduleControl from '../components/admin/ScheduleControl'
import { useConfirm } from '../hooks/useConfirm'
import { CATEGORIES } from '../lib/categories'
import { CATEGORY_ICONS } from '../lib/mediaIcons'
import toast from 'react-hot-toast'

const USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,50}$/

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
  password: '',
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
  const [editMode, setEditMode] = useState(null) // null | 'password' | 'display_name'
  const [newPassword, setNewPassword] = useState('')
  const [newDisplayName, setNewDisplayName] = useState('')
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

  const handlePasswordSave = async () => {
    if (!newPassword.trim()) return
    setSaving(true)
    try {
      await client.put(`/users/${user.id}`, { password: newPassword })
      toast.success('Password updated')
      setEditMode(null)
      setNewPassword('')
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
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
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
            {isSelf && (
              <span className="text-xs text-gray-400">(you)</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Added {new Date(user.created_at).toLocaleDateString()}
          </p>
        </div>

        {/* Inline edit panel for password or display name */}
        {editMode === 'password' ? (
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password"
              className="w-36 text-base sm:text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              autoFocus
            />
            <button onClick={handlePasswordSave} disabled={saving} className="p-1 rounded-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20">
              <Check size={14} />
            </button>
            <button onClick={() => { setEditMode(null); setNewPassword('') }} className="p-1 rounded-sm text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
              <X size={14} />
            </button>
          </div>
        ) : editMode === 'display_name' ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder={user.display_name || 'Display name'}
              maxLength={100}
              className="w-36 text-base sm:text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              autoFocus
            />
            <button onClick={handleDisplayNameSave} disabled={saving} className="p-1 rounded-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20">
              <Check size={14} />
            </button>
            <button onClick={() => { setEditMode(null); setNewDisplayName('') }} className="p-1 rounded-sm text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <button
              onClick={() => { setEditMode('display_name'); setNewDisplayName(user.display_name || '') }}
              title="Edit display name"
              className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Pencil size={14} />
            </button>
            <button
              onClick={() => setEditMode('password')}
              title="Reset password"
              className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
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

export default function Admin() {
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
    if (form.password.length < 8) {
      errors.password = 'Password must be at least 8 characters'
    }
    setFormErrors(errors)
    if (Object.keys(errors).length > 0) return

    setCreating(true)
    try {
      await client.post('/users', { ...form, display_name: form.display_name.trim() || undefined })
      toast.success(`User "${form.username}" created`)
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage users and system settings</p>
      </div>

      {/* System info card */}
      <SystemInfoPanel />

      {/* Users card */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Users</h2>
          <Button size="sm" onClick={() => setShowForm((s) => !s)}>
            <Plus size={14} /> New user
          </Button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} className="mb-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 space-y-3">
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
              placeholder="Shown in ownership labels — defaults to username"
            />
            <Input
              label="Password"
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              error={formErrors.password}
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

      {/* Ownership mode card */}
      <OwnershipPanel />

      {/* Medium visibility card */}
      <MediumVisibilityPanel />

      {/* Backup card */}
      <BackupPanel />

      {/* Plex integration card */}
      <PlexIntegrationPanel />

      {/* Library maintenance card */}
      <LibraryMaintenancePanel />

      {/* Danger zone */}
      <DangerZonePanel />
    </div>
  )
}

const API_LABELS = [
  { key: 'tmdb', label: 'TMDB' },
  { key: 'igdb', label: 'IGDB' },
  { key: 'upcdatabase', label: 'UPCDatabase.org' },
]

function SystemInfoPanel() {
  const [info, setInfo] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    adminApi.systemInfo().then(setInfo).catch(() => setFailed(true))
  }, [])

  // The backend container doesn't know its own externally-mapped port (that's
  // a docker-compose/host-level detail) — the browser's own URL is the only
  // reliable source for "what port am I actually talking to this on".
  const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Info size={16} className="text-gray-400" />
        <h2 className="font-semibold text-gray-900 dark:text-white">System Info</h2>
      </div>

      {failed ? (
        <p className="text-sm text-red-500">Could not load system info.</p>
      ) : !info ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : (
        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Version</dt>
            <dd className="text-gray-900 dark:text-white font-medium">v{info.version}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Status</dt>
            <dd className="flex items-center gap-1.5 text-gray-900 dark:text-white font-medium">
              <span className="h-2 w-2 rounded-full bg-green-500 shrink-0" />
              Online
            </dd>
          </div>
          <div>
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Database</dt>
            <dd className="text-gray-900 dark:text-white font-medium">{info.database}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Port</dt>
            <dd className="text-gray-900 dark:text-white font-medium">{port}</dd>
          </div>
          <div className="col-span-2 sm:col-span-4">
            <dt className="text-xs text-gray-400 uppercase tracking-wide mb-1.5">Metadata APIs</dt>
            <dd className="flex flex-wrap gap-2">
              {API_LABELS.map(({ key, label }) => (
                <span
                  key={key}
                  className={clsx(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs',
                    info.apis[key]
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
                  )}
                >
                  {info.apis[key] ? <Check size={11} /> : <X size={11} />}
                  {label}
                </span>
              ))}
            </dd>
          </div>
        </dl>
      )}
    </div>
  )
}

function OwnershipPanel() {
  const { setAppConfig } = useReferenceDataStore()
  const [config, setConfig] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [migrating, setMigrating] = useState(false)
  const [migrateUserId, setMigrateUserId] = useState('')
  const [showMigrateForm, setShowMigrateForm] = useState(false)

  useEffect(() => {
    Promise.all([appConfigApi.get(), usersApi.summary()])
      .then(([cfg, us]) => {
        setConfig(cfg)
        setUsers(us.filter((u) => !u.is_system))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleSetShared = async () => {
    setSaving(true)
    try {
      const updated = await appConfigApi.update({ ownership_mode: 'shared' })
      setConfig(updated)
      setAppConfig(updated)
      toast.success('Ownership mode set to Shared')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleMigrate = async () => {
    if (!migrateUserId) return toast.error('Select a user to assign existing items to')
    setMigrating(true)
    try {
      const updated = await appConfigApi.migrateOwnership({ target_user_id: Number(migrateUserId) })
      setConfig(updated)
      setAppConfig(updated)
      setShowMigrateForm(false)
      setMigrateUserId('')
      toast.success('Ownership migrated and mode set to By User')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setMigrating(false)
    }
  }

  if (loading) return null

  const isShared = config?.ownership_mode === 'shared'

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Users size={16} className="text-gray-400" />
        <h2 className="font-semibold text-gray-900 dark:text-white">Ownership Mode</h2>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 -mt-2">
        Control how items and lists are assigned to user accounts.
      </p>

      <div className="space-y-3">
        <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
          isShared
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
        }`}>
          <input
            type="radio"
            name="ownership_mode"
            value="shared"
            checked={isShared}
            onChange={handleSetShared}
            className="mt-0.5"
            disabled={saving || migrating}
          />
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Shared</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              All items and lists belong to a shared household account by default. Users can still
              assign individual items or lists to their own login.
            </p>
          </div>
        </label>

        <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
          !isShared
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
        }`}>
          <input
            type="radio"
            name="ownership_mode"
            value="by_user"
            checked={!isShared}
            onChange={() => setShowMigrateForm(true)}
            className="mt-0.5"
            disabled={saving || migrating || !isShared}
          />
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">By User</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Each item and list defaults to the account of whoever added it. Great for households
              where multiple people maintain separate collections.
            </p>
          </div>
        </label>
      </div>

      {showMigrateForm && isShared && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4 space-y-3">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
            Assign existing items to a user
          </p>
          <p className="text-xs text-amber-700 dark:text-amber-400">
            All currently shared items, lists, and Plex mappings will be reassigned to the user
            you choose below. New items will default to whoever adds them.
          </p>
          <select
            className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            value={migrateUserId}
            onChange={(e) => setMigrateUserId(e.target.value)}
          >
            <option value="">Select a user…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.display_name || u.username}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => { setShowMigrateForm(false); setMigrateUserId('') }}
              disabled={migrating}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              loading={migrating}
              disabled={!migrateUserId}
              onClick={handleMigrate}
            >
              Migrate &amp; Switch to By User
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function MediumVisibilityPanel() {
  const { setAppConfig } = useReferenceDataStore()
  const stats = useStatsStore((s) => s.stats)
  const [config, setConfig] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    appConfigApi.get().then(setConfig).catch(() => {})
  }, [])

  const handleToggle = async (categoryValue) => {
    if (!config || saving) return
    const current = config.disabled_categories ?? []
    const updated = current.includes(categoryValue)
      ? current.filter((c) => c !== categoryValue)
      : [...current, categoryValue]
    setSaving(true)
    try {
      const result = await appConfigApi.update({ disabled_categories: updated })
      setConfig(result)
      // Directly update the reference store so navbar reflects the change
      // immediately — calling invalidate() would clear appConfig to null and
      // cause a flash of all categories until the next ensureLoaded() fires.
      setAppConfig(result)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-1">Medium Visibility</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Disable mediums you don&apos;t use — they&apos;ll be hidden from all navigation and add flows.
      </p>
      {!config ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : (
        <div className="space-y-2">
          {CATEGORIES.map((c) => {
            const Icon = CATEGORY_ICONS[c.value]
            const isEnabled = !(config.disabled_categories ?? []).includes(c.value)
            const count = stats?.by_category?.[c.value] ?? null
            return (
              <label key={c.value} className="flex items-center gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={() => handleToggle(c.value)}
                  disabled={saving}
                  className="rounded-sm"
                />
                <Icon size={16} className="text-gray-500 dark:text-gray-400 shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">{c.label}</span>
                {count !== null && (
                  <span className="text-xs text-gray-400 ml-auto">{count.toLocaleString()}</span>
                )}
              </label>
            )
          })}
        </div>
      )}
    </div>
  )
}

function BackupPanel() {
  const [backups, setBackups] = useState([])
  const [backupSupported, setBackupSupported] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [confirm, confirmDialog] = useConfirm()
  const backupSchedule = useAdminSchedule('backup')

  const loadBackups = () => {
    client.get('/library/backup/list').then((r) => {
      setBackups(r.data.backups)
      setBackupSupported(r.data.backup_supported)
    }).catch(() => {})
  }

  useEffect(() => { loadBackups() }, [])

  const triggerBackup = async () => {
    setTriggering(true)
    try {
      const r = await client.post('/library/backup')
      toast.success(`Backup created: ${r.data.backup}`)
      loadBackups()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setTriggering(false)
    }
  }

  const downloadBackup = async (name) => {
    try {
      const resp = await client.get(`/library/backup/${name}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = name
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.error(err.message)
    }
  }

  const deleteBackup = async (name) => {
    if (!await confirm(`Delete backup ${name}? This cannot be undone.`)) return
    try {
      await client.delete(`/library/backup/${name}`)
      loadBackups()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900 dark:text-white">Database Backups</h2>
        {backupSupported && (
          <Button size="sm" variant="secondary" loading={triggering} onClick={triggerBackup}>
            Backup now
          </Button>
        )}
      </div>
      {!backupSupported ? (
        <p className="text-sm text-gray-400">
          Built-in backups are only available for the bundled SQLite database. This instance is
          configured to use PostgreSQL — back it up using your PostgreSQL provider&apos;s own
          tools (e.g. <code className="font-mono">pg_dump</code>).
        </p>
      ) : (
        <>
          {backups.length === 0 ? (
            <p className="text-sm text-gray-400">No backups yet. Click &quot;Backup now&quot; to create one.</p>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {backups.map((b) => (
                <div key={b.name} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-xs text-gray-600 dark:text-gray-400">{b.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {(b.size_bytes / 1024).toFixed(0)} KB · {new Date(b.created).toLocaleString()}
                    </span>
                    <button
                      onClick={() => downloadBackup(b.name)}
                      title="Download backup"
                      className="p-1 rounded-sm text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      <Download size={13} />
                    </button>
                    <button
                      onClick={() => deleteBackup(b.name)}
                      title="Delete backup"
                      className="p-1 rounded-sm text-gray-400 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-xs text-gray-400">
            Backups are stored in the <code className="font-mono">app_data</code> volume. The last 30 are retained automatically.
          </p>
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Scheduled backups</p>
            <ScheduleControl
              schedule={backupSchedule.schedule}
              canManage
              saving={backupSchedule.saving}
              deleting={backupSchedule.deleting}
              onSave={backupSchedule.handleSave}
              onDelete={backupSchedule.handleDelete}
            />
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400 space-y-1">
            <p className="font-medium text-gray-700 dark:text-gray-300">To restore a backup:</p>
            <ol className="list-decimal list-inside space-y-0.5">
              <li>Download the backup file above.</li>
              <li>Stop the Armarium containers (<code className="font-mono">docker compose down</code>).</li>
              <li>Replace the database file in the <code className="font-mono">app_data</code> volume with the downloaded backup, renaming it to match the configured database filename.</li>
              <li>Restart the containers (<code className="font-mono">docker compose up -d</code>).</li>
            </ol>
          </div>
        </>
      )}
      {confirmDialog}
    </div>
  )
}

function PlexIntegrationPanel() {
  const [config, setConfig] = useState(null)
  const [baseUrl, setBaseUrl] = useState('')
  const [token, setToken] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [platformId, setPlatformId] = useState('')
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirm, confirmDialog] = useConfirm()
  const { platforms, ensureLoaded } = useReferenceDataStore()

  useEffect(() => {
    ensureLoaded()
    plexApi.getConfig()
      .then((c) => {
        setConfig(c)
        setBaseUrl(c.base_url || '')
        setEnabled(c.configured ? c.enabled : true)
        if (c.platform?.id) setPlatformId(String(c.platform.id))
      })
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false))
  }, [ensureLoaded])

  // Pre-select a platform literally named "Plex" once the reference data has
  // loaded, but only if there's no configured platform to prefer already.
  useEffect(() => {
    if (platformId || config?.configured) return
    const plex = platforms.find((p) => p.name === 'Plex')
    if (plex) setPlatformId(String(plex.id))
  }, [platforms, config, platformId])

  const handleTest = async () => {
    if (!baseUrl || !token) {
      toast.error('Enter both the server URL and token to test the connection')
      return
    }
    setTesting(true)
    try {
      const r = await plexApi.testConnection({ base_url: baseUrl, token })
      toast.success(`Connected to ${r.name || 'Plex server'} (v${r.version})`)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!baseUrl) {
      toast.error('Server URL is required')
      return
    }
    if (!platformId) {
      toast.error('Choose a platform for synced Plex media')
      return
    }
    setSaving(true)
    try {
      const r = await plexApi.updateConfig({ base_url: baseUrl, token: token || undefined, enabled, platform_id: Number(platformId) })
      setConfig(r)
      setToken('')
      toast.success('Plex configuration saved')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async () => {
    if (!await confirm(
      'Remove the Plex integration? Existing Plex-sourced items are left in place, ' +
      'but library sync mappings will stop working until reconfigured.',
      { confirmLabel: 'Remove' }
    )) return
    try {
      await plexApi.deleteConfig()
      setConfig({ configured: false, enabled: false, base_url: null, platform: null })
      setBaseUrl('')
      setToken('')
      setEnabled(true)
      setPlatformId('')
      toast.success('Plex integration removed')
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-1">Plex Integration</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Connect a local Plex Media Server to sync your Films &amp; TV and Music libraries.
        Once configured, set up library mappings in Settings → Plex Sync.
      </p>
      {loading ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : (
        <div className="space-y-3 max-w-md">
          <Input
            label="Server URL"
            placeholder="http://192.168.1.10:32400"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <Input
            label="Token"
            type="password"
            placeholder={config?.configured ? 'Unchanged' : 'Plex authentication token'}
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded-sm"
            />
            Enabled
          </label>
          {platforms.length === 0 ? (
            <p className="text-sm text-amber-600 dark:text-amber-400">
              Create a platform in <Link to="/settings/platforms" className="underline">Settings → Platforms</Link> first —
              synced films, shows and music need a platform to be filed under.
            </p>
          ) : (
            <SelectMenu
              label="Platform"
              groups={[{ options: [
                { value: '', label: 'Select a platform…' },
                ...platforms.map((p) => ({ value: String(p.id), label: p.name, platform: p })),
              ] }]}
              value={platformId}
              onChange={setPlatformId}
              renderIcon={(opt) => opt.platform && <PlatformLogo platform={opt.platform} className="h-5 w-5" />}
            />
          )}
          <p className="text-xs text-gray-400">
            All films, TV shows and music synced from Plex are filed as digital media under this platform.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" loading={testing} onClick={handleTest}>
              Test connection
            </Button>
            <Button size="sm" loading={saving} disabled={platforms.length === 0} onClick={handleSave}>
              Save
            </Button>
            {config?.configured && (
              <Button size="sm" variant="danger" onClick={handleRemove}>
                <Trash2 size={14} /> Remove integration
              </Button>
            )}
          </div>
        </div>
      )}
      {confirmDialog}
    </div>
  )
}

function useAdminSchedule(jobType) {
  const [schedule, setSchedule] = useState(undefined)   // undefined = not loaded yet
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    schedulesApi.get(jobType)
      .then((s) => setSchedule(s))
      .catch(() => setSchedule(null))
  }, [jobType])

  const handleSave = async (data) => {
    setSaving(true)
    try {
      const s = await schedulesApi.upsert(jobType, data)
      setSchedule(s)
      toast.success('Schedule saved')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await schedulesApi.delete(jobType)
      setSchedule(null)
      toast.success('Schedule removed')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setDeleting(false)
    }
  }

  return { schedule: schedule ?? null, saving, deleting, handleSave, handleDelete }
}

function MaintenanceRow({ label, description, action, schedule, onSave, onDelete, saving, deleting, showExportDir = false }) {
  return (
    <div className="py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{label}</p>
          {description && <p className="text-xs text-gray-400 mt-0.5">{description}</p>}
          <div className="mt-1.5">
            <ScheduleControl
              schedule={schedule}
              canManage
              showExportDir={showExportDir}
              saving={saving}
              deleting={deleting}
              onSave={onSave}
              onDelete={onDelete}
            />
          </div>
        </div>
        {action}
      </div>
    </div>
  )
}

function LibraryMaintenancePanel() {
  const [linking, setLinking] = useState(false)
  const [redownloading, setRedownloading] = useState(false)
  const [purging, setPurging] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const autoLink = useAdminSchedule('auto_link')
  const redownload = useAdminSchedule('redownload_covers')
  const purge = useAdminSchedule('purge_covers')
  const exportCoversSchedule = useAdminSchedule('export_covers')

  const handleAutoLink = async () => {
    if (!await confirm(
      'This scans your whole library and links items that share the same film/show, ' +
      'album or book (by TMDB/MusicBrainz ID or ISBN) but aren\'t linked yet — useful ' +
      'after adding copies on other platforms or locations before linking existed. Continue?',
      { confirmLabel: 'Scan & Link', variant: 'secondary' }
    )) return
    setLinking(true)
    try {
      const r = await adminApi.autoLink()
      toast.success(`Linked ${r.linked} item${r.linked === 1 ? '' : 's'}`)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLinking(false)
    }
  }

  const handleRedownload = async () => {
    if (!await confirm(
      'This re-downloads and re-processes every cover image fetched from a URL. ' +
      'It runs in the background and may take a while for large libraries. Continue?',
      { confirmLabel: 'Redownload', variant: 'secondary' }
    )) return
    setRedownloading(true)
    try {
      const r = await adminApi.redownloadCovers()
      toast.success(`Redownloading ${r.queued} cover${r.queued === 1 ? '' : 's'}…`)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRedownloading(false)
    }
  }

  const handlePurge = async () => {
    if (!await confirm(
      'This permanently deletes any cover image files on disk that are no longer ' +
      'referenced by an item. Continue?',
      { confirmLabel: 'Purge' }
    )) return
    setPurging(true)
    try {
      const r = await adminApi.purgeOrphanCovers()
      toast.success(`Deleted ${r.deleted} orphaned file${r.deleted === 1 ? '' : 's'}`)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setPurging(false)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      await exportCovers()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-1">Library Maintenance</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
        Run now or set a recurring schedule for each maintenance task.
      </p>
      <div>
        <MaintenanceRow
          label="Scan & link duplicate copies"
          description="Links items that share a TMDB/MusicBrainz ID or ISBN across platforms."
          schedule={autoLink.schedule}
          onSave={autoLink.handleSave}
          onDelete={autoLink.handleDelete}
          saving={autoLink.saving}
          deleting={autoLink.deleting}
          action={
            <Button size="sm" variant="secondary" loading={linking} onClick={handleAutoLink}>
              <Link2 size={14} /> Run now
            </Button>
          }
        />
        <MaintenanceRow
          label="Redownload all covers"
          description="Re-fetches and re-optimises covers from their original URLs."
          schedule={redownload.schedule}
          onSave={redownload.handleSave}
          onDelete={redownload.handleDelete}
          saving={redownload.saving}
          deleting={redownload.deleting}
          action={
            <Button size="sm" variant="secondary" loading={redownloading} onClick={handleRedownload}>
              <RefreshCw size={14} /> Run now
            </Button>
          }
        />
        <MaintenanceRow
          label="Purge orphan covers"
          description="Deletes cover image files on disk that no item references."
          schedule={purge.schedule}
          onSave={purge.handleSave}
          onDelete={purge.handleDelete}
          saving={purge.saving}
          deleting={purge.deleting}
          action={
            <Button size="sm" variant="secondary" loading={purging} onClick={handlePurge}>
              <Trash2 size={14} /> Run now
            </Button>
          }
        />
        <MaintenanceRow
          label="Export covers"
          description="Saves a zip of all cover images to the server. Scheduled exports save to a date-named folder; once per day maximum."
          showExportDir
          schedule={exportCoversSchedule.schedule}
          onSave={exportCoversSchedule.handleSave}
          onDelete={exportCoversSchedule.handleDelete}
          saving={exportCoversSchedule.saving}
          deleting={exportCoversSchedule.deleting}
          action={
            <Button size="sm" variant="secondary" loading={exporting} onClick={handleExport}>
              <Download size={14} /> Download now
            </Button>
          }
        />
      </div>
      {confirmDialog}
    </div>
  )
}

function DangerZonePanel() {
  const [resetting, setResetting] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const handleReset = async () => {
    if (!await confirm(
      'This will permanently delete all media, locations, and platforms, and restore the default mediums. ' +
      'User accounts are kept.\n\nMake sure you’ve taken a backup first.',
      { title: 'Reset database?', confirmLabel: 'Continue', variant: 'danger' }
    )) return

    if (!await confirm(
      'Last chance — this cannot be undone. Type RESET below to permanently wipe the library.',
      { title: 'Confirm database reset', confirmLabel: 'Reset database', variant: 'danger', requireText: 'RESET' }
    )) return

    setResetting(true)
    try {
      await adminApi.resetDatabase()
      toast.success('Database reset to default')
      window.location.reload()
    } catch (err) {
      toast.error(err.message)
      setResetting(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-red-200 dark:border-red-900/40 p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle size={18} className="text-red-500" />
        <h2 className="font-semibold text-gray-900 dark:text-white">Danger Zone</h2>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
        Reset the database to its default state — all media, locations, and platforms will be
        permanently deleted, and the default mediums will be restored. User accounts are
        not affected.
      </p>
      <Button size="sm" variant="danger" loading={resetting} onClick={handleReset}>
        <Trash2 size={14} /> Reset database
      </Button>
      {confirmDialog}
    </div>
  )
}
