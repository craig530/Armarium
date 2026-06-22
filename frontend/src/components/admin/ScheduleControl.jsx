import { useState } from 'react'
import { Calendar, Clock, Trash2, X } from 'lucide-react'
import Button from '../ui/Button'

const INTERVAL_OPTIONS = [
  { value: 1, label: 'Every hour' },
  { value: 6, label: 'Every 6 hours' },
  { value: 12, label: 'Every 12 hours' },
  { value: 24, label: 'Daily' },
  { value: 168, label: 'Weekly' },
]

function intervalLabel(hours) {
  const opt = INTERVAL_OPTIONS.find((o) => o.value === hours)
  return opt ? opt.label : `Every ${hours}h`
}

function formatNextRun(dt) {
  if (!dt) return null
  const d = new Date(dt)
  const now = new Date()
  const diffMs = d - now
  if (diffMs < 0) return 'soon'
  if (diffMs < 60000) return 'in < 1 min'
  if (diffMs < 3600000) return `in ${Math.round(diffMs / 60000)} min`
  if (diffMs < 86400000) return `in ${Math.round(diffMs / 3600000)}h`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatLastRun(dt) {
  if (!dt) return null
  const d = new Date(dt)
  const diffMs = new Date() - d
  if (diffMs < 60000) return 'just now'
  if (diffMs < 3600000) return `${Math.round(diffMs / 60000)} min ago`
  if (diffMs < 86400000) return `${Math.round(diffMs / 3600000)}h ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/**
 * Reusable schedule management inline widget.
 *
 * Props:
 *   schedule       — current ScheduleResponse from API (null if none)
 *   onSave(data)   — called with {interval_hours, ...extra} to create/update
 *   onDelete()     — called to remove schedule
 *   canManage      — boolean: show edit controls
 *   showAutoRemove — show the "auto-remove stale" checkbox (Plex sync only)
 *   showExportDir  — show the export base directory input (export_covers only)
 *   saving         — loading state for the save button
 *   deleting       — loading state for the delete button
 */
export default function ScheduleControl({
  schedule,
  onSave,
  onDelete,
  canManage = true,
  showAutoRemove = false,
  showExportDir = false,
  saving = false,
  deleting = false,
}) {
  const [editing, setEditing] = useState(false)
  const [intervalHours, setIntervalHours] = useState(
    schedule?.interval_hours ?? 24
  )
  const [autoRemove, setAutoRemove] = useState(
    schedule?.auto_remove_stale ?? true
  )
  const [exportDir, setExportDir] = useState(schedule?.export_base_dir ?? '')

  const openEdit = () => {
    setIntervalHours(schedule?.interval_hours ?? 24)
    setAutoRemove(schedule?.auto_remove_stale ?? true)
    setExportDir(schedule?.export_base_dir ?? '')
    setEditing(true)
  }

  const handleSave = () => {
    const data = { interval_hours: intervalHours }
    if (showAutoRemove) data.auto_remove_stale = autoRemove
    if (showExportDir && exportDir) data.export_base_dir = exportDir
    onSave(data)
    setEditing(false)
  }

  if (!schedule && !canManage) return null

  if (!schedule) {
    // No schedule — show "Add schedule" if canManage
    if (editing) {
      return (
        <ScheduleForm
          intervalHours={intervalHours}
          setIntervalHours={setIntervalHours}
          autoRemove={autoRemove}
          setAutoRemove={setAutoRemove}
          exportDir={exportDir}
          setExportDir={setExportDir}
          showAutoRemove={showAutoRemove}
          showExportDir={showExportDir}
          onSave={handleSave}
          onCancel={() => setEditing(false)}
          saving={saving}
        />
      )
    }
    return (
      <button
        onClick={openEdit}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
      >
        <Calendar size={12} />
        Add schedule
      </button>
    )
  }

  // Schedule exists
  const nextRun = formatNextRun(schedule.next_run_at)
  const lastRun = formatLastRun(schedule.last_run_at)
  const lastRunFailed = schedule.last_run_status === 'error'

  if (editing) {
    return (
      <ScheduleForm
        intervalHours={intervalHours}
        setIntervalHours={setIntervalHours}
        autoRemove={autoRemove}
        setAutoRemove={setAutoRemove}
        exportDir={exportDir}
        setExportDir={setExportDir}
        showAutoRemove={showAutoRemove}
        showExportDir={showExportDir}
        onSave={handleSave}
        onCancel={() => setEditing(false)}
        saving={saving}
      />
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
      <span className="flex items-center gap-1.5 shrink-0">
        <Clock size={12} className="shrink-0" />
        {intervalLabel(schedule.interval_hours)}
      </span>
      {lastRun && (
        <span
          className={lastRunFailed ? 'text-red-500' : 'text-gray-400'}
          title={lastRunFailed ? schedule.last_run_error || 'Last run failed' : undefined}
        >
          last ran {lastRun}{lastRunFailed ? ' (failed)' : ''}
        </span>
      )}
      {nextRun && <span className="text-gray-400">next {nextRun}</span>}
      {canManage && (
        <span className="flex items-center gap-2 shrink-0">
          <button
            onClick={openEdit}
            className="text-gray-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
            title="Edit schedule"
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
            title="Remove schedule"
          >
            <Trash2 size={11} />
          </button>
        </span>
      )}
    </div>
  )
}

function ScheduleForm({
  intervalHours, setIntervalHours,
  autoRemove, setAutoRemove,
  exportDir, setExportDir,
  showAutoRemove, showExportDir,
  onSave, onCancel, saving,
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-800/50">
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-600 dark:text-gray-400 shrink-0">Repeat</label>
        <select
          value={intervalHours}
          onChange={(e) => setIntervalHours(Number(e.target.value))}
          className="text-xs rounded-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 focus:outline-hidden focus:ring-2 focus:ring-brand-500"
        >
          {INTERVAL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      {showAutoRemove && (
        <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRemove}
            onChange={(e) => setAutoRemove(e.target.checked)}
            className="rounded-sm"
          />
          Auto-remove items no longer in Plex
        </label>
      )}
      {showExportDir && (
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-600 dark:text-gray-400 shrink-0">Export to</label>
          <input
            type="text"
            value={exportDir}
            onChange={(e) => setExportDir(e.target.value)}
            placeholder="e.g. /backups/covers (date folder added automatically)"
            className="flex-1 text-xs rounded-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 focus:outline-hidden focus:ring-2 focus:ring-brand-500 min-w-0"
          />
        </div>
      )}
      <div className="flex gap-2">
        <Button size="sm" loading={saving} onClick={onSave}>Save</Button>
        <button
          onClick={onCancel}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <X size={12} /> Cancel
        </button>
      </div>
    </div>
  )
}
