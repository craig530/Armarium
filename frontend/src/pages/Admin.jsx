import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, Shield, ShieldOff, Check, X, RefreshCw, AlertTriangle, Download, Link2 } from 'lucide-react'
import client from '../api/client'
import { adminApi } from '../api/admin'
import { plexApi } from '../api/plex'
import { exportCovers } from '../lib/export'
import { useAuthStore, useReferenceDataStore } from '../store'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import SelectMenu from '../components/ui/SelectMenu'
import PlatformLogo from '../components/ui/PlatformLogo'
import { useConfirm } from '../hooks/useConfirm'
import toast from 'react-hot-toast'

const USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,50}$/

const PERMISSION_FLAGS = [
  { key: 'can_add_items', label: 'Add items' },
  { key: 'can_manage_locations', label: 'Manage locations' },
  { key: 'can_manage_platforms', label: 'Manage platforms' },
  { key: 'can_manage_media_types', label: 'Manage media types' },
]

const EMPTY_FORM = {
  username: '',
  password: '',
  is_admin: false,
  is_read_only: false,
  can_add_items: true,
  can_manage_locations: true,
  can_manage_platforms: true,
  can_manage_media_types: false,
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
  const [editing, setEditing] = useState(false)
  const [newPassword, setNewPassword] = useState('')
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

  const handlePasswordReset = async () => {
    if (!newPassword.trim()) return
    setSaving(true)
    try {
      await client.put(`/users/${user.id}`, { password: newPassword })
      toast.success('Password updated')
      setEditing(false)
      setNewPassword('')
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

  return (
    <div className="py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-white">{user.username}</span>
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

        {/* Password reset inline */}
        {editing ? (
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password"
              className="w-36 text-base sm:text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              autoFocus
            />
            <button onClick={handlePasswordReset} disabled={saving} className="p-1 rounded-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20">
              <Check size={14} />
            </button>
            <button onClick={() => { setEditing(false); setNewPassword('') }} className="p-1 rounded-sm text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setEditing(true)}
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
      await client.post('/users', form)
      toast.success(`User "${form.username}" created`)
      setShowForm(false)
      setForm({ ...EMPTY_FORM })
      setFormErrors({})
      load()
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

      {/* Backup card */}
      <BackupPanel />

      {/* Plex integration card */}
      <PlexIntegrationPanel />

      {/* Cover images card */}
      <CoverImagesPanel />

      {/* Library maintenance card */}
      <LibraryMaintenancePanel />

      {/* Danger zone */}
      <DangerZonePanel />
    </div>
  )
}

function BackupPanel() {
  const [backups, setBackups] = useState([])
  const [triggering, setTriggering] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const loadBackups = () => {
    client.get('/library/backup/list').then((r) => setBackups(r.data.backups)).catch(() => {})
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
        <Button size="sm" variant="secondary" loading={triggering} onClick={triggerBackup}>
          Backup now
        </Button>
      </div>
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
      <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400 space-y-1">
        <p className="font-medium text-gray-700 dark:text-gray-300">To restore a backup:</p>
        <ol className="list-decimal list-inside space-y-0.5">
          <li>Download the backup file above.</li>
          <li>Stop the Armarium containers (<code className="font-mono">docker compose down</code>).</li>
          <li>Replace the database file in the <code className="font-mono">app_data</code> volume with the downloaded backup, renaming it to match the configured database filename.</li>
          <li>Restart the containers (<code className="font-mono">docker compose up -d</code>).</li>
        </ol>
      </div>
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
      'but library sync mappings will stop working until reconfigured.'
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

function CoverImagesPanel() {
  const [redownloading, setRedownloading] = useState(false)
  const [purging, setPurging] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const handleRedownload = async () => {
    if (!await confirm(
      'This re-downloads and re-processes every cover image fetched from a URL, ' +
      'fixing any that were saved with the previous image processing. It runs in ' +
      'the background and may take a while for large libraries. Continue?'
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
      'referenced by an item. Continue?'
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
      <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Cover Images</h2>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" loading={redownloading} onClick={handleRedownload}>
          <RefreshCw size={14} /> Redownload all
        </Button>
        <Button size="sm" variant="secondary" loading={purging} onClick={handlePurge}>
          <Trash2 size={14} /> Purge orphans
        </Button>
        <Button size="sm" variant="secondary" loading={exporting} onClick={handleExport}>
          <Download size={14} /> Export covers
        </Button>
      </div>
      {confirmDialog}
    </div>
  )
}

function LibraryMaintenancePanel() {
  const [linking, setLinking] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const handleAutoLink = async () => {
    if (!await confirm(
      'This scans your whole library and links items that share the same film/show, ' +
      'album or book (by TMDB/MusicBrainz ID or ISBN) but aren\'t linked yet — useful ' +
      'after adding copies on other platforms or locations before linking existed. Continue?'
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

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-1">Library Maintenance</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Find and link copies of the same item across different platforms or locations
        that aren&apos;t linked yet.
      </p>
      <Button size="sm" variant="secondary" loading={linking} onClick={handleAutoLink}>
        <Link2 size={14} /> Scan &amp; link duplicate copies
      </Button>
      {confirmDialog}
    </div>
  )
}

function DangerZonePanel() {
  const [resetting, setResetting] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const handleReset = async () => {
    if (!await confirm(
      'This will permanently delete all media, locations, and platforms, and restore the default media types. ' +
      'User accounts are kept.\n\nMake sure you’ve taken a backup first. Continue?'
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
        permanently deleted, and the default media types will be restored. User accounts are
        not affected.
      </p>
      <Button size="sm" variant="danger" loading={resetting} onClick={handleReset}>
        <Trash2 size={14} /> Reset database
      </Button>
      {confirmDialog}
    </div>
  )
}
