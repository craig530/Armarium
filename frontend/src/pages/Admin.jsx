import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { Trash2, Check, X, RefreshCw, AlertTriangle, Download, Link2, Users, Info, ChevronRight } from 'lucide-react'
import client from '../api/client'
import { adminApi } from '../api/admin'
import { plexApi } from '../api/plex'
import { schedulesApi } from '../api/schedules'
import { appConfigApi } from '../api/appConfig'
import { usersApi } from '../api/users'
import { exportCovers } from '../lib/export'
import { useReferenceDataStore, useStatsStore } from '../store'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import SelectMenu from '../components/ui/SelectMenu'
import PlatformLogo from '../components/ui/PlatformLogo'
import ScheduleControl from '../components/admin/ScheduleControl'
import { useConfirm } from '../hooks/useConfirm'
import { CATEGORIES } from '../lib/categories'
import { CATEGORY_ICONS } from '../lib/mediaIcons'
import toast from 'react-hot-toast'

function UsersPanel() {
  const [count, setCount] = useState(null)

  useEffect(() => {
    usersApi.summary().then((us) => setCount(us.length)).catch(() => {})
  }, [])

  return (
    <Link
      to="/admin/users"
      className="flex items-center justify-between bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
    >
      <div className="flex items-center gap-3">
        <Users size={18} className="text-gray-400 shrink-0" />
        <div>
          <h2 className="font-semibold text-gray-900 dark:text-white">Users</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {count === null ? 'Loading…' : `${count} user${count === 1 ? '' : 's'}`}
          </p>
        </div>
      </div>
      <ChevronRight size={18} className="text-gray-400 shrink-0" />
    </Link>
  )
}

export default function Admin() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage users and system settings</p>
      </div>

      {/* System info card */}
      <SystemInfoPanel />

      {/* Users card */}
      <UsersPanel />

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

  // The browser's own URL is the only reliable source for "what port is this
  // request actually arriving on" — e.g. 443 when accessed through a reverse
  // proxy terminating HTTPS. info.configured_port is the separate PORT value
  // from .env/docker-compose (the host port docker maps to the container),
  // which can easily differ from the externally-visible one.
  const connectedPort = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')

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
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Connected via</dt>
            <dd className="text-gray-900 dark:text-white font-medium">port {connectedPort}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-400 uppercase tracking-wide">Configured port</dt>
            <dd className="text-gray-900 dark:text-white font-medium">{info.configured_port}</dd>
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
        Disable mediums you don&apos;t use, and they&apos;ll be hidden from all navigation and add flows.
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
          configured to use PostgreSQL. Back it up using your PostgreSQL provider&apos;s own
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
              Create a platform in <Link to="/settings/platforms" className="underline">Settings → Platforms</Link> first.
              Synced films, shows and music need a platform to be filed under.
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
      'album or book (by TMDB/MusicBrainz ID or ISBN) but aren\'t linked yet. Useful ' +
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
      'Last chance: this cannot be undone. Type RESET below to permanently wipe the library.',
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
        Reset the database to its default state. All media, locations, and platforms will be
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
