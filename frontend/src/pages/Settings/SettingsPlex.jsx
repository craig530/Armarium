import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

import { plexApi } from '../../api/plex'
import { MediaSubtypeBadge } from '../../components/ui/Badge'
import CoverImage from '../../components/media/CoverImage'
import PlatformLogo from '../../components/ui/PlatformLogo'
import Button from '../../components/ui/Button'
import ScheduleControl from '../../components/admin/ScheduleControl'
import { categoryLabel } from '../../lib/categories'
import { useConfirm } from '../../hooks/useConfirm'
import { usePlexSyncGuard } from '../../hooks/usePlexSyncGuard'
import { useAuthStore, useReferenceDataStore } from '../../store'

function SyncStatusBadge({ status }) {
  if (!status) return null
  if (status === 'completed') return <CheckCircle size={12} className="text-green-500" />
  if (status === 'error') return <XCircle size={12} className="text-red-500" />
  if (status === 'cancelled') return <AlertCircle size={12} className="text-amber-500" />
  return null
}

function LastSyncSummary({ mapping }) {
  if (!mapping.last_synced_at) return <span className="text-xs text-gray-400">Never synced</span>

  const when = new Date(mapping.last_synced_at).toLocaleString()
  const parts = []
  if (mapping.last_sync_created != null) parts.push(`${mapping.last_sync_created} added`)
  if (mapping.last_sync_updated != null) parts.push(`${mapping.last_sync_updated} updated`)
  if (mapping.last_sync_removed != null && mapping.last_sync_removed > 0) parts.push(`${mapping.last_sync_removed} removed`)

  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400 flex-wrap">
      <SyncStatusBadge status={mapping.last_sync_status} />
      <span>{when}</span>
      {parts.length > 0 && <span className="text-gray-300 dark:text-gray-600">·</span>}
      {parts.length > 0 && <span>{parts.join(', ')}</span>}
      {mapping.last_sync_status === 'error' && mapping.last_sync_error && (
        <span className="text-red-400 truncate max-w-[200px]" title={mapping.last_sync_error}>
          — {mapping.last_sync_error}
        </span>
      )}
    </div>
  )
}

export default function SettingsPlex() {
  const { user } = useAuthStore()
  const isAdmin = !!user?.is_admin
  const canManageSchedules = isAdmin || !!user?.can_manage_schedules
  const { mediaSubtypes, users, ensureLoaded } = useReferenceDataStore()
  const [config, setConfig] = useState(null)
  const [sections, setSections] = useState([])
  const [mappings, setMappings] = useState([])
  const [schedules, setSchedules] = useState({})   // mapping_id -> ScheduleResponse | null
  const [loading, setLoading] = useState(true)
  const [syncStatus, setSyncStatus] = useState({})
  const [syncResult, setSyncResult] = useState(null)
  const [staleSelection, setStaleSelection] = useState({})
  const [removingStale, setRemovingStale] = useState(false)
  // Manual sync options per mapping_id
  const [syncOptions, setSyncOptions] = useState({})  // mapping_id -> { autoRemove: bool }
  const [scheduleSaving, setScheduleSaving] = useState({})
  const [scheduleDeleting, setScheduleDeleting] = useState({})
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
          const added = status.result?.created ?? 0
          const updated = status.result?.updated ?? 0
          const removed = status.result?.removed ?? 0
          const parts = [`${added} added`, `${updated} updated`]
          if (removed > 0) parts.push(`${removed} removed`)
          toast.success(`"${mapping.section_title}": ${parts.join(', ')}`)
          setSyncResult({ mapping, ...status.result })
          setStaleSelection(Object.fromEntries((status.result?.stale_items ?? []).map((i) => [i.id, true])))
          await load()
          useReferenceDataStore.getState().invalidate()
        } else if (status.status === 'cancelled') {
          toast(`"${mapping.section_title}" sync cancelled`)
          setSyncResult({ mapping, ...status.result })
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

        // Load sync statuses and schedules in parallel
        const [statuses, scheduleResults] = await Promise.all([
          Promise.all(m.map((mapping) => plexApi.getSyncStatus(mapping.id))),
          Promise.all(m.map((mapping) =>
            plexApi.getMappingSchedule(mapping.id).catch(() => null)
          )),
        ])

        setSyncStatus((prev) => {
          const next = { ...prev }
          m.forEach((mapping, i) => { next[mapping.id] = statuses[i] })
          return next
        })
        const scheduleMap = {}
        m.forEach((mapping, i) => { scheduleMap[mapping.id] = scheduleResults[i] })
        setSchedules(scheduleMap)

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

  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleOwnerChange = async (mapping, ownerId) => {
    try {
      const updated = await plexApi.updateMapping(mapping.id, {
        media_subtype_id: mapping.media_subtype?.id,
        owner_id: ownerId ? Number(ownerId) : null,
      })
      setMappings((prev) => prev.map((m) => (m.id === mapping.id ? updated : m)))
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  const handleDelete = async (mapping) => {
    if (!await confirm(
      `Stop syncing "${mapping.section_title}"? Items already added from this library are kept.`,
      { confirmLabel: 'Stop syncing', variant: 'secondary' }
    )) return
    try {
      await plexApi.deleteMapping(mapping.id)
      toast.success('Library mapping removed')
      if (syncResult?.mapping.id === mapping.id) {
        setSyncResult(null)
        setStaleSelection({})
      }
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    }
  }

  const handleSync = async (mapping) => {
    const opts = syncOptions[mapping.id] || {}
    try {
      const status = await plexApi.syncMapping(mapping.id, { auto_remove_stale: !!opts.autoRemove })
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

  const handleSaveSchedule = async (mapping, data) => {
    setScheduleSaving((p) => ({ ...p, [mapping.id]: true }))
    try {
      const sched = await plexApi.upsertMappingSchedule(mapping.id, data)
      setSchedules((p) => ({ ...p, [mapping.id]: sched }))
      toast.success('Schedule saved')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setScheduleSaving((p) => ({ ...p, [mapping.id]: false }))
    }
  }

  const handleDeleteSchedule = async (mapping) => {
    if (!await confirm('Remove the sync schedule for this library?', { confirmLabel: 'Remove', variant: 'secondary' })) return
    setScheduleDeleting((p) => ({ ...p, [mapping.id]: true }))
    try {
      await plexApi.deleteMappingSchedule(mapping.id)
      setSchedules((p) => ({ ...p, [mapping.id]: null }))
      toast.success('Schedule removed')
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message)
    } finally {
      setScheduleDeleting((p) => ({ ...p, [mapping.id]: false }))
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
    if (ids.length === 0) { handleKeepAllStale(); return }
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
          Match Plex libraries to your Films &amp; TV and Music collections and sync them in.
        </p>
      </div>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5">
        {loading ? (
          <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
        ) : !config?.configured || !config?.enabled ? (
          <div className="text-center py-8 space-y-3">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Plex isn&apos;t configured yet. Set up the connection in Admin to enable library sync.
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
                Synced media is filed under{' '}
                <span className="font-medium text-gray-700 dark:text-gray-300">{config.platform.name}</span>
              </div>
            )}

            <section>
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">Synced libraries</h3>
              {mappings.length === 0 ? (
                <p className="text-sm text-gray-400">No libraries added yet.</p>
              ) : (
                <div className="space-y-3">
                  {mappings.map((m) => {
                    const subtypeOptions = mediaSubtypes.filter(
                      (s) => s.category === m.category && s.supertype === 'digital'
                    )
                    const status = syncStatus[m.id]
                    const isSyncing = status?.status === 'running'
                    const opts = syncOptions[m.id] || {}
                    const schedule = schedules[m.id]

                    return (
                      <div key={m.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3 space-y-2">
                        <div className="flex items-start gap-3">
                          <MediaSubtypeBadge subtype={{ category: m.category, name: categoryLabel(m.category) }} />
                          <span className="flex-1 min-w-0 text-sm text-gray-800 dark:text-gray-200 break-words">{m.section_title}</span>
                          <button
                            onClick={() => handleDelete(m)}
                            disabled={isSyncing}
                            title="Stop syncing this library"
                            className="p-1 -m-1 rounded-sm text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        {/* Sync status / progress */}
                        <div className="flex flex-wrap items-center gap-2">
                          {isSyncing ? (
                            <>
                              <div className="flex items-center gap-2 flex-1 min-w-32">
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
                            <LastSyncSummary mapping={m} />
                          )}
                        </div>

                        {/* Manual sync options + trigger */}
                        {!isSyncing && (
                          <div className="flex flex-wrap items-center gap-3">
                            <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none">
                              <input
                                type="checkbox"
                                checked={!!opts.autoRemove}
                                onChange={(e) =>
                                  setSyncOptions((p) => ({
                                    ...p,
                                    [m.id]: { ...p[m.id], autoRemove: e.target.checked },
                                  }))
                                }
                                className="rounded-sm"
                              />
                              Auto-remove missing items
                            </label>
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={!m.media_subtype}
                              onClick={() => handleSync(m)}
                            >
                              <RefreshCw size={13} /> Sync now
                            </Button>
                          </div>
                        )}

                        {/* Medium selector */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-gray-400 shrink-0">Medium:</span>
                          {isAdmin ? (
                            <select
                              value={m.media_subtype?.id ?? ''}
                              onChange={(e) => handleSubtypeChange(m, e.target.value)}
                              className="text-xs rounded-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 focus:outline-hidden focus:ring-2 focus:ring-brand-500"
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

                        {/* Owner selector */}
                        {users.length > 0 && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-gray-400 shrink-0">Owner:</span>
                            {isAdmin ? (
                              <select
                                value={m.owner_id ?? ''}
                                onChange={(e) => handleOwnerChange(m, e.target.value)}
                                className="text-xs rounded-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                              >
                                <option value="">Shared</option>
                                {users.map((u) => (
                                  <option key={u.id} value={u.id}>{u.username}</option>
                                ))}
                              </select>
                            ) : (
                              <span className="text-xs text-gray-600 dark:text-gray-300">
                                {m.owner_username || 'Shared'}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Schedule */}
                        <div className="pt-1 border-t border-gray-100 dark:border-gray-800">
                          <ScheduleControl
                            schedule={schedule}
                            canManage={canManageSchedules}
                            showAutoRemove
                            saving={scheduleSaving[m.id]}
                            deleting={scheduleDeleting[m.id]}
                            onSave={(data) => handleSaveSchedule(m, data)}
                            onDelete={() => handleDeleteSchedule(m)}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>

            {syncResult && (syncResult.stale_items?.length ?? 0) > 0 && (
              <section className="space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">
                    No longer in &quot;{syncResult.mapping.section_title}&quot; ({syncResult.stale_items.length})
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
                          className="h-4 w-4 rounded-sm border-gray-300 text-brand-600 focus:ring-brand-500"
                        />
                        <CoverImage src={item.cover_thumb_url} category={item.category} title={item.title} size="sm" />
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
