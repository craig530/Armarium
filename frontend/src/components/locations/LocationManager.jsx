import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { locationsApi } from '../../api/locations'
import Input, { Select } from '../ui/Input'
import Button from '../ui/Button'
import LocationIcon from '../ui/LocationIcon'
import IconPicker from '../settings/IconPicker'
import toast from 'react-hot-toast'

const EMPTY_FORM = { name: '', parent_id: '', icon_key: '', icon_url: null }

export default function LocationManager() {
  const [locations, setLocations] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)

  const load = () => {
    locationsApi.list().then(setLocations).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const flatLocations = []
  const flatten = (locs, depth = 0) => {
    for (const loc of locs) {
      flatLocations.push({ ...loc, depth })
      if (loc.children?.length) flatten(loc.children, depth + 1)
    }
  }
  flatten(locations)

  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('Name required')
    try {
      const payload = {
        name: form.name,
        parent_id: form.parent_id ? Number(form.parent_id) : null,
        icon_key: form.icon_key || null,
      }
      if (editId) {
        await locationsApi.update(editId, payload)
        toast.success('Location updated')
      } else {
        await locationsApi.create(payload)
        toast.success('Location created')
      }
      setShowForm(false)
      setEditId(null)
      setForm(EMPTY_FORM)
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleEdit = (loc) => {
    setEditId(loc.id)
    setForm({ name: loc.name, parent_id: loc.parent_id || '', icon_key: loc.icon_key || '', icon_url: loc.icon_url || null })
    setShowForm(true)
  }

  const handleDelete = async (loc) => {
    if (!confirm(`Delete "${loc.name}"? Items will be unassigned.`)) return
    try {
      await locationsApi.delete(loc.id)
      toast.success('Location deleted')
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleIconUpload = async (file) => {
    if (!editId) return
    try {
      const updated = await locationsApi.uploadIcon(editId, file)
      setForm((f) => ({ ...f, icon_url: updated.icon_url }))
      toast.success('Icon uploaded')
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Manage locations</h2>
        <Button size="sm" onClick={() => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true) }}>
          <Plus size={15} /> New location
        </Button>
      </div>

      {/* Add/Edit form */}
      {showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {editId ? 'Edit location' : 'New location'}
          </h3>
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Bookshelf, Living Room"
            autoFocus
          />
          <Select
            label="Parent location (optional)"
            value={form.parent_id}
            onChange={(e) => setForm((f) => ({ ...f, parent_id: e.target.value }))}
          >
            <option value="">— No parent (top level) —</option>
            {flatLocations
              .filter((l) => l.id !== editId)
              .map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {'  '.repeat(loc.depth)}{loc.name}
                </option>
              ))}
          </Select>
          <IconPicker
            iconKey={form.icon_key || null}
            iconUrl={form.icon_url}
            onSelect={(key) => setForm((f) => ({ ...f, icon_key: key || '' }))}
            onUpload={editId ? handleIconUpload : undefined}
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleSave}>
              <Check size={14} /> Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
              <X size={14} /> Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Tree with edit/delete per node */}
      {loading ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : (
        <div className="space-y-0.5">
          {locations.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No locations yet.</p>
          ) : (
            flatLocations.map((loc) => (
              <div
                key={loc.id}
                className="flex items-center gap-2 py-1"
                style={{ paddingLeft: `${loc.depth * 20}px` }}
              >
                <LocationIcon location={loc} size={16} className="shrink-0 text-gray-400 dark:text-gray-500" />
                <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">
                  {'└ '.repeat(loc.depth > 0 ? 1 : 0)}{loc.name}
                </span>
                {loc.item_count > 0 && (
                  <span className="text-xs text-gray-400">{loc.item_count} items</span>
                )}
                <button
                  onClick={() => handleEdit(loc)}
                  className="p-1 rounded text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <Pencil size={13} />
                </button>
                <button
                  onClick={() => handleDelete(loc)}
                  className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
