import { useState, useEffect } from 'react'
import { Plus, Trash2, Shield, ShieldOff, Check, X, RefreshCw } from 'lucide-react'
import client from '../api/client'
import { useAuthStore } from '../store'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import toast from 'react-hot-toast'

function UserRow({ user, currentUserId, onUpdated, onDeleted }) {
  const [editing, setEditing] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)

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
    if (!confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    try {
      await client.delete(`/users/${user.id}`)
      toast.success('User deleted')
      onDeleted(user.id)
    } catch (err) {
      toast.error(err.message)
    }
  }

  const isSelf = user.id === currentUserId

  return (
    <div className="flex items-center gap-3 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
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
            className="w-36 text-sm rounded-lg border px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            autoFocus
          />
          <button onClick={handlePasswordReset} disabled={saving} className="p-1 rounded text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20">
            <Check size={14} />
          </button>
          <button onClick={() => { setEditing(false); setNewPassword('') }} className="p-1 rounded text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
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
            disabled={isSelf}
            title={user.is_admin ? 'Remove admin' : 'Grant admin'}
            className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"
          >
            {user.is_admin ? <ShieldOff size={14} /> : <Shield size={14} />}
          </button>
          <button
            onClick={handleToggleActive}
            disabled={isSelf}
            title={user.is_active ? 'Deactivate' : 'Activate'}
            className="p-1.5 rounded-lg text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-30"
          >
            {user.is_active ? <X size={14} /> : <Check size={14} />}
          </button>
          <button
            onClick={handleDelete}
            disabled={isSelf}
            title="Delete user"
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30"
          >
            <Trash2 size={14} />
          </button>
        </div>
      )}
    </div>
  )
}

export default function Admin() {
  const { user: currentUser } = useAuthStore()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', is_admin: false })
  const [creating, setCreating] = useState(false)

  const load = () => {
    setLoading(true)
    client.get('/users').then((r) => setUsers(r.data)).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.username || !form.password) return
    setCreating(true)
    try {
      await client.post('/users', form)
      toast.success(`User "${form.username}" created`)
      setShowForm(false)
      setForm({ username: '', password: '', is_admin: false })
      load()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setCreating(false)
    }
  }

  // Find current user's ID from the list (we need the DB id, not from the token)
  const currentDbUser = users.find((u) => u.username === currentUser?.username)

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
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => setForm((f) => ({ ...f, is_admin: e.target.checked }))}
                className="rounded"
              />
              Grant admin role
            </label>
            <div className="flex gap-2">
              <Button size="sm" type="submit" loading={creating}>Create</Button>
              <Button size="sm" variant="ghost" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
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
                onUpdated={load}
                onDeleted={(id) => setUsers((us) => us.filter((u) => u.id !== id))}
              />
            ))}
          </div>
        )}
      </div>

      {/* Backup card */}
      <BackupPanel />
    </div>
  )
}

function BackupPanel() {
  const [backups, setBackups] = useState([])
  const [triggering, setTriggering] = useState(false)

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

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900 dark:text-white">Database Backups</h2>
        <Button size="sm" variant="secondary" loading={triggering} onClick={triggerBackup}>
          Backup now
        </Button>
      </div>
      {backups.length === 0 ? (
        <p className="text-sm text-gray-400">No backups yet. Click "Backup now" to create one.</p>
      ) : (
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {backups.map((b) => (
            <div key={b.name} className="flex items-center justify-between text-sm">
              <span className="font-mono text-xs text-gray-600 dark:text-gray-400">{b.name}</span>
              <span className="text-xs text-gray-400">
                {(b.size_bytes / 1024).toFixed(0)} KB · {new Date(b.created).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
      <p className="mt-3 text-xs text-gray-400">
        Backups are stored in the <code className="font-mono">app_data</code> volume. The last 30 are retained automatically.
      </p>
    </div>
  )
}
