import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

import { plexApi } from '../../api/plex'
import { MediaSubtypeBadge } from '../../components/ui/Badge'
import PlatformLogo from '../../components/ui/PlatformLogo'
import Button from '../../components/ui/Button'
import { categoryLabel } from '../../lib/categories'
import { useConfirm } from '../../hooks/useConfirm'
import { useReferenceDataStore } from '../../store'

export default function SettingsPlex() {
  const [config, setConfig] = useState(null)
  const [sections, setSections] = useState([])
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(true)
  const [confirm, confirmDialog] = useConfirm()

  const load = async () => {
    try {
      const c = await plexApi.getConfig()
      setConfig(c)
      if (c.configured && c.enabled) {
        const [s, m] = await Promise.all([plexApi.getSections(), plexApi.listMappings()])
        setSections(s)
        setMappings(m)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAdd = async (sectionKey) => {
    try {
      await plexApi.createMapping({ section_key: sectionKey })
      toast.success('Library added')
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  const handleDelete = async (mapping) => {
    if (!await confirm(`Stop syncing "${mapping.section_title}"? Items already added from this library are kept.`)) return
    try {
      await plexApi.deleteMapping(mapping.id)
      toast.success('Library mapping removed')
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
  }

  if (!config?.configured || !config?.enabled) {
    return (
      <div className="text-center py-8 space-y-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Plex isn't configured yet. Set up the connection in Admin to enable library sync.
        </p>
        <Link to="/admin">
          <Button size="sm" variant="secondary">Go to Admin</Button>
        </Link>
      </div>
    )
  }

  const unmapped = sections.filter((s) => !s.mapped)

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">Synced libraries</h3>
        {mappings.length === 0 ? (
          <p className="text-sm text-gray-400">No libraries added yet.</p>
        ) : (
          <div className="space-y-1">
            {mappings.map((m) => (
              <div key={m.id} className="flex items-center gap-3 py-1.5">
                <MediaSubtypeBadge subtype={{ category: m.category, name: categoryLabel(m.category) }} />
                <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{m.section_title}</span>
                <PlatformLogo platform={m.platform} className="h-6 w-6" />
                <span className="text-xs text-gray-400">
                  {m.last_synced_at ? `Synced ${new Date(m.last_synced_at).toLocaleString()}` : 'Never synced'}
                </span>
                <button
                  onClick={() => handleDelete(m)}
                  className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">Available libraries</h3>
        {unmapped.length === 0 ? (
          <p className="text-sm text-gray-400">No additional libraries found on the Plex server.</p>
        ) : (
          <div className="space-y-1">
            {unmapped.map((s) => (
              <div key={s.key} className="flex items-center gap-3 py-1.5">
                <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{s.title}</span>
                <span className="text-xs text-gray-400 capitalize">{s.type}</span>
                <Button size="sm" variant="ghost" onClick={() => handleAdd(s.key)}>
                  <Plus size={14} /> Add
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>

      {confirmDialog}
    </div>
  )
}
