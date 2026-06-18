import { useState, useEffect } from 'react'
import { Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { appConfigApi } from '../../api/appConfig'
import { usersApi } from '../../api/users'
import Button from '../../components/ui/Button'
import { useReferenceDataStore } from '../../store'

export default function SettingsOwnership() {
  const { invalidate } = useReferenceDataStore()
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
        setUsers(us)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleSetShared = async () => {
    setSaving(true)
    try {
      const updated = await appConfigApi.update({ ownership_mode: 'shared' })
      setConfig(updated)
      invalidate()
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
      invalidate()
      setShowMigrateForm(false)
      setMigrateUserId('')
      toast.success('Ownership migrated and mode set to By Login')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setMigrating(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Loading…</p>
  }

  const isShared = config?.ownership_mode === 'shared'

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Library Ownership</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Control how items and lists are assigned to user accounts.
        </p>
      </div>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Users size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Ownership Mode</h2>
        </div>

        <div className="space-y-3">
          {/* Shared mode */}
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

          {/* By Login mode */}
          <label className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
            !isShared
              ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
              : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
          }`}>
            <input
              type="radio"
              name="ownership_mode"
              value="by_login"
              checked={!isShared}
              onChange={() => setShowMigrateForm(true)}
              className="mt-0.5"
              disabled={saving || migrating || !isShared}
            />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">By Login</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Each item and list defaults to the account of whoever added it. Great for households
                where multiple people maintain separate collections. Digital items show whose
                service to use.
              </p>
            </div>
          </label>
        </div>

        {/* Migration form — shown when switching from Shared → By Login */}
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
                <option key={u.id} value={u.id}>{u.username}</option>
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
                Migrate &amp; Switch to By Login
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
