import { useState, useEffect, useRef } from 'react'
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
import { usePlexSyncGuard } from '../../hooks/usePlexSyncGuard'
import { useAuthStore, useReferenceDataStore } from '../../store'

export default function SettingsPlex() {
  const { user } = useAuthStore()
  const isAdmin = !!user?.is_admin
  const { mediaSubtypes, ensureLoaded } = useReferenceDataStore()
  const [config, setConfig] = useState(null)
  const [sections, setSections] = useState([])
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncStatus, setSyncStatus] = useState({})
  const [syncResult, setSyncResult] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [resolving, setResolving] = useState(false)
  const [staleSelection, setStaleSelection] = useState({})
  const [removingStale, setRemovingStale] = useState(false)
  const [confirm, confirmDialog] = useConfirm()
  const pollIntervals = useRef({})
  const syncGuardDialog = usePlexSyncGuard(syncStatus)

  const startPolling = (mapping) => {
    if (pollIntervals.current[mapping.id]) return
    pollIntervals.current[mapping.id] = setInterval(async () => {
      try {
        const status = await plexApi.getSyncStatus(mapping.id)
        setSyncStatus((prev) => ({ ...prev, [mapping.id]: status }))
        if (status.status === 'running') return

        clearInterval(pollIntervals.current[mapping.id])
        delete pollIntervals.current[mapping.id]

        if (status.status === 'completed') {
          toast.success(`"${mapping.section_title}": ${status.result.created} added, ${status.result.updated} updated`)
          setSyncResult({ mapping, ...status.result })
          setResolutions({})
          setStaleSelection(Object.fromEntries(status.result.stale_items.map((i) => [i.id, true])))
          await load()
          useReferenceDataStore.getState().invalidate()
        } else if (status.status === 'cancelled') {
          toast(`"${mapping.section_title}" sync cancelled — ${status.result.created} added, ${status.result.updated} updated before stopping`)
          setSyncResult({ mapping, ...status.result })
          setResolutions({})
          setStaleSelection({})
          await load()
          useReferenceDataStore.getState().invalidate()
        } else if (status.status === 'error') {
          toast.error(status.error || 'Sync failed')
        }
      } catch (err) {
        clearInterval(pollIntervals.current[mapping.id])
        delete pollIntervals.current[mapping.id]
        toast.error(err.response?.data?.detail || err.message)
      }
    }, 1000)
  }

  const load = async () => {
    try {
      const c = await plexApi.getConfig()
      setConfig(c)
      if (c.configured && c.enabled) {
        const [s, m] = await Promise.all([plexApi.getSections(), plexApi.listMappings()])
        setSections(s)
        setMappings(m)

        const statuses = await Promise.all(m.map((mapping) => plexApi.getSyncStatus(mapping.id)))
        setSyncStatus((prev) => {
          const next = { ...prev }
          m.forEach((mapping, i) => { next[mapping.id] = statuses[i] })
          return next
        })
        m.forEach((mapping, i) => {
          if (statuses[i].status === 'running') startPolling(mapping)
        })
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  useEffect(() => { ensureLoaded() }, [ensureLoaded])
  useEffect(() => () => {
    Object.values(pollIntervals.current).forEach(clearInterval)
  }, [])

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

  const handleSubtypeChange = async (mapping, subtypeId) => {
    if (!subtypeId) return
    try {
      const updated = await plexApi.updateMapping(mapping.id, { media_subtype_id: Number(subtypeId) })
      setMappings((prev) => prev.map((m) => (m.id === mapping.id ? updated : m)))
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
    try {
      const status = await plexApi.syncMapping(mapping.id)
      setSyncStatus((prev) => ({ ...prev, [mapping.id]: status }))
      startPolling(mapping)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  const handleCancel = async (mapping) => {
    try {
      const status = await plexApi.cancelSync(mapping.id)
      setSyncStatus((prev) => ({ ...prev, [mapping.id]: status }))
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
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

  const unmapped = sections.filter((s) => !s.mapped)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Plex Sync</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Match Plex libraries to your Films & TV and Music collections and sync them in.
        </p>
      </div>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5">
        {loading ? (
          <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
        ) : !config?.configured || !config?.enabled ? (
          <div className="text-center py-8 space-y-3">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Plex isn't configured yet. Set up the connection in Admin to enable library sync.
            </p>
            <Link to="/admin">
              <Button size="sm" variant="secondary">Go to Admin</Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {config.platform && (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <PlatformLogo platform={config.platform} className="h-5 w-5" />
                Synced media is filed under <span className="font-medium text-gray-700 dark:text-gray-300">{config.platform.name}</span>
              </div>
            )}
            <section>
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">Synced libraries</h3>
              {mappings.length === 0 ? (
                <p className="text-sm text-gray-400">No libraries added yet.</p>
              ) : (
                <div className="space-y-2">
                  {mappings.map((m) => {
                    const subtypeOptions = mediaSubtypes.filter(
                      (s) => s.category === m.category && s.supertype === 'digital'
                    )
                    const status = syncStatus[m.id]
                    const isSyncing = status?.status === 'running'
                    return (
                      <div key={m.id} className="py-1">
                        <div className="flex items-center gap-3">
                          <MediaSubtypeBadge subtype={{ category: m.category, name: categoryLabel(m.category) }} />
                          <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{m.section_title}</span>
                          {isSyncing ? (
                            <>
                              <div className="flex items-center gap-2 w-36">
                                <div className="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                                  <div
                                    className="h-full bg-brand-500 transition-all"
                                    style={{
                                      width: status.total
                                        ? `${Math.min(100, (status.processed / status.total) * 100)}%`
                                        : '15%',
                                    }}
                                  />
                                </div>
                                <span className="text-xs text-gray-400 whitespace-nowrap">
                                  {status.processed}/{status.total ?? '?'}
                                </span>
                              </div>
                              <Button size="sm" variant="danger" onClick={() => handleCancel(m)}>
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <>
                              <span className="text-xs text-gray-400">
                                {m.last_synced_at ? `Synced ${new Date(m.last_synced_at).toLocaleString()}` : 'Never synced'}
                              </span>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={!m.media_subtype}
                                onClick={() => handleSync(m)}
                              >
                                <RefreshCw size={13} /> Sync now
                              </Button>
                            </>
                          )}
                          <button
                            onClick={() => handleDelete(m)}
                            disabled={isSyncing}
                            className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                        <div className="flex items-center gap-2 mt-1 ml-1">
                          <span className="text-xs text-gray-400">Media type:</span>
                          {isAdmin ? (
                            <select
                              value={m.media_subtype?.id ?? ''}
                              onChange={(e) => handleSubtypeChange(m, e.target.value)}
                              className="text-xs rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
                            >
                              <option value="" disabled>Select…</option>
                              {subtypeOptions.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                              ))}
                            </select>
                          ) : m.media_subtype ? (
                            <span className="text-xs text-gray-600 dark:text-gray-300">{m.media_subtype.name}</span>
                          ) : (
                            <span className="text-xs text-amber-500">
                              Not set — ask an admin to configure this in Plex Sync settings
                            </span>
                          )}
                          {!m.media_subtype && isAdmin && (
                            <span className="text-xs text-amber-500">— sync disabled until set</span>
                          )}
                        </div>
                      </div>
                    )
                  })}
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
        )}
      </div>
      {syncGuardDialog}
    </div>
  )
}
