import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Check, X, ChevronUp, ChevronDown } from 'lucide-react'
import { mediaSubtypesApi } from '../../api/mediaSubtypes'
import { CATEGORIES, SUPERTYPES } from '../../lib/categories'
import Input, { Select } from '../ui/Input'
import Button from '../ui/Button'
import { useAuthStore, hasPermission, useReferenceDataStore } from '../../store'
import { useConfirm } from '../../hooks/useConfirm'
import toast from 'react-hot-toast'

const EMPTY_FORM = { name: '', category: CATEGORIES[0].value, supertype: SUPERTYPES[0].value }

export default function MediaSubtypeManager() {
  const { user } = useAuthStore()
  const canManage = hasPermission(user, 'can_manage_media_types')
  const [subtypes, setSubtypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [confirm, confirmDialog] = useConfirm()

  const load = () => {
    mediaSubtypesApi.list().then(setSubtypes).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('Name required')
    try {
      if (editId) {
        await mediaSubtypesApi.update(editId, { name: form.name })
        toast.success('Media type updated')
      } else {
        await mediaSubtypesApi.create(form)
        toast.success('Media type created')
      }
      setShowForm(false)
      setEditId(null)
      setForm(EMPTY_FORM)
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleEdit = (subtype) => {
    setEditId(subtype.id)
    setForm({ name: subtype.name, category: subtype.category, supertype: subtype.supertype })
    setShowForm(true)
  }

  const handleDelete = async (subtype) => {
    if (!await confirm(`Delete "${subtype.name}"?`)) return
    try {
      await mediaSubtypesApi.delete(subtype.id)
      toast.success('Media type deleted')
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  // Re-sequences the group to 0..N-1 in the new (swapped) order, rather than
  // just swapping the two `sort_order` values directly — new subtypes all
  // default to `sort_order: 0`, so a same-value swap between tied entries
  // would otherwise be a no-op. Only entries whose target index differs from
  // their current `sort_order` are written.
  const move = async (subtype, direction, group) => {
    const idx = group.findIndex((s) => s.id === subtype.id)
    const swapIdx = idx + direction
    if (swapIdx < 0 || swapIdx >= group.length) return
    const reordered = [...group]
    ;[reordered[idx], reordered[swapIdx]] = [reordered[swapIdx], reordered[idx]]
    const updates = reordered
      .map((s, i) => ({ id: s.id, sort_order: i, changed: s.sort_order !== i }))
      .filter((u) => u.changed)
    try {
      await Promise.all(updates.map((u) => mediaSubtypesApi.update(u.id, { sort_order: u.sort_order })))
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      {canManage && (
        <div className="flex items-center justify-end">
          <Button size="sm" onClick={() => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true) }}>
            <Plus size={15} /> New type
          </Button>
        </div>
      )}

      {/* Add/Edit form */}
      {canManage && showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {editId ? 'Edit media type' : 'New media type'}
          </h3>
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. CD, Blu-ray, Streaming Film"
            autoFocus
          />
          {!editId && (
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Category"
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              >
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </Select>
              <Select
                label="Format"
                value={form.supertype}
                onChange={(e) => setForm((f) => ({ ...f, supertype: e.target.value }))}
              >
                {SUPERTYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </Select>
            </div>
          )}
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

      {/* Grouped list */}
      {loading ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : subtypes.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">No media types yet.</p>
      ) : (
        <div className="space-y-5">
          {CATEGORIES.map((category) => {
            const categorySubtypes = subtypes.filter((s) => s.category === category.value)
            if (categorySubtypes.length === 0) return null
            return (
              <div key={category.value} className="space-y-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{category.label}</h3>
                {SUPERTYPES.map((supertype) => {
                  const group = categorySubtypes
                    .filter((s) => s.supertype === supertype.value)
                    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
                  if (group.length === 0) return null
                  return (
                    <div key={supertype.value} className="pl-3 space-y-0.5">
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{supertype.label}</p>
                      {group.map((subtype, idx) => (
                        <div key={subtype.id} className="flex items-center gap-2 py-1">
                          {canManage && (
                            <div className="flex flex-col -my-1">
                              <button
                                onClick={() => move(subtype, -1, group)}
                                disabled={idx === 0}
                                className="p-0.5 text-gray-300 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                              >
                                <ChevronUp size={12} />
                              </button>
                              <button
                                onClick={() => move(subtype, 1, group)}
                                disabled={idx === group.length - 1}
                                className="p-0.5 text-gray-300 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                              >
                                <ChevronDown size={12} />
                              </button>
                            </div>
                          )}
                          <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{subtype.name}</span>
                          {subtype.item_count > 0 && (
                            <span className="text-xs text-gray-400">{subtype.item_count} items</span>
                          )}
                          {canManage && (
                            <>
                              <button
                                onClick={() => handleEdit(subtype)}
                                className="p-1 rounded text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                              >
                                <Pencil size={13} />
                              </button>
                              <button
                                onClick={() => handleDelete(subtype)}
                                className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      )}

      {confirmDialog}
    </div>
  )
}
