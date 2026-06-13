import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

import { plexApi } from '../../api/plex'
import { MediaSubtypeBadge } from '../../components/ui/Badge'
import CoverImage from '../../components/media/CoverImage'
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
  const [syncingId, setSyncingId] = useState(null)
  const [syncResult, setSyncResult] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [resolving, setResolving] = useState(false)
  const [staleSelection, setStaleSelection] = useState({})
  const [removingStale, setRemovingStale] = useState(false)
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
      if (syncResult?.mapping.id === mapping.id) {
        setSyncResult(null)
        setResolutions({})
        setStaleSelection({})
      }
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  const handleSync = async (mapping) => {
    setSyncingId(mapping.id)
    try {
      const result = await plexApi.syncMapping(mapping.id)
      toast.success(`"${mapping.section_title}": ${result.created} added, ${result.updated} updated`)
      setSyncResult({ mapping, ...result })
      setResolutions({})
      setStaleSelection(Object.fromEntries(result.stale_items.map((i) => [i.id, true])))
      await load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setSyncingId(null)
    }
  }

  const handleStageResolution = (existingItemId, choice) => {
    setResolutions((prev) => ({ ...prev, [existingItemId]: choice }))
  }

  const handleResolveDone = async () => {
    const staged = syncResult.conflicts
      .filter((c) => resolutions[c.existing_item.id])
      .map((c) => ({
        existing_item_id: c.existing_item.id,
        plex_item: c.plex_item,
        resolution: resolutions[c.existing_item.id],
      }))
    if (staged.length === 0) {
      setSyncResult((prev) => ({ ...prev, conflicts: [] }))
      return
    }
    setResolving(true)
    try {
      await plexApi.resolveConflicts(syncResult.mapping.id, staged)
      toast.success(`Resolved ${staged.length} item${staged.length === 1 ? '' : 's'}`)
      const remaining = syncResult.conflicts.filter((c) => !resolutions[c.existing_item.id])
      setSyncResult((prev) => ({ ...prev, conflicts: remaining }))
      setResolutions({})
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setResolving(false)
    }
  }

  const handleToggleStale = (itemId) => {
    setStaleSelection((prev) => ({ ...prev, [itemId]: !prev[itemId] }))
  }

  const handleKeepAllStale = () => {
    setSyncResult((prev) => ({ ...prev, stale_items: [] }))
    setStaleSelection({})
  }

  const handleRemoveStale = async () => {
    const ids = syncResult.stale_items.filter((i) => staleSelection[i.id]).map((i) => i.id)
    if (ids.length === 0) {
      handleKeepAllStale()
      return
    }
    setRemovingStale(true)
    try {
      const result = await plexApi.removeStaleItems(syncResult.mapping.id, ids)
      toast.success(`Removed ${result.removed} item${result.removed === 1 ? '' : 's'}`)
      const remaining = syncResult.stale_items.filter((i) => !staleSelection[i.id])
      setSyncResult((prev) => ({ ...prev, stale_items: remaining }))
      setStaleSelection({})
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setRemovingStale(false)
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
                <Button size="sm" variant="ghost" loading={syncingId === m.id} onClick={() => handleSync(m)}>
                  <RefreshCw size={13} /> Sync now
                </Button>
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

      {syncResult && (syncResult.conflicts.length > 0 || syncResult.stale_items.length > 0) && (
        <section className="space-y-4">
          {syncResult.conflicts.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">
                Possible duplicates from "{syncResult.mapping.section_title}" ({syncResult.conflicts.length})
              </h3>
              <p className="text-xs text-gray-400 mb-2">
                These items already exist in your library. Choose whether to keep your version or
                replace it with Plex's info — either way it'll be tracked as synced from this library.
              </p>
              <div className="space-y-1">
                {syncResult.conflicts.map((c) => {
                  const choice = resolutions[c.existing_item.id]
                  return (
                    <div key={c.existing_item.id} className="flex items-center gap-3 py-1.5">
                      <CoverImage
                        src={c.existing_item.cover_thumb_url}
                        category={c.existing_item.category}
                        title={c.existing_item.title}
                        size="sm"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800 dark:text-gray-200 truncate">{c.existing_item.title}</p>
                        <p className="text-xs text-gray-400">
                          {c.existing_item.year}
                          {c.plex_item.year && c.plex_item.year !== c.existing_item.year ? ` · Plex: ${c.plex_item.year}` : ''}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant={choice === 'keep_mine' ? 'primary' : 'outline'}
                        onClick={() => handleStageResolution(c.existing_item.id, 'keep_mine')}
                      >
                        Keep mine
                      </Button>
                      <Button
                        size="sm"
                        variant={choice === 'use_plex' ? 'primary' : 'outline'}
                        onClick={() => handleStageResolution(c.existing_item.id, 'use_plex')}
                      >
                        Use Plex info
                      </Button>
                    </div>
                  )
                })}
              </div>
              <div className="pt-2">
                <Button size="sm" variant="secondary" loading={resolving} onClick={handleResolveDone}>
                  Done
                </Button>
              </div>
            </div>
          )}

          {syncResult.stale_items.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">
                No longer in "{syncResult.mapping.section_title}" ({syncResult.stale_items.length})
              </h3>
              <p className="text-xs text-gray-400 mb-2">
                These items were previously synced from Plex but no longer exist there. Checked
                items will be removed from your library.
              </p>
              <div className="space-y-1">
                {syncResult.stale_items.map((item) => (
                  <label key={item.id} className="flex items-center gap-3 py-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!staleSelection[item.id]}
                      onChange={() => handleToggleStale(item.id)}
                      className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                    />
                    <CoverImage
                      src={item.cover_thumb_url}
                      category={item.category}
                      title={item.title}
                      size="sm"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-800 dark:text-gray-200 truncate">{item.title}</p>
                      <p className="text-xs text-gray-400">{item.year}</p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="pt-2 flex gap-2">
                <Button size="sm" variant="danger" loading={removingStale} onClick={handleRemoveStale}>
                  Remove selected
                </Button>
                <Button size="sm" variant="secondary" onClick={handleKeepAllStale}>
                  Keep all
                </Button>
              </div>
            </div>
          )}
        </section>
      )}

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
