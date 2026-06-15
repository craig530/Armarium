import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { listsApi } from '../../api/lists'
import { CATEGORIES, categoryLabel } from '../../lib/categories'
import Input, { Select } from '../ui/Input'
import Button from '../ui/Button'
import { useAuthStore, hasPermission, useReferenceDataStore } from '../../store'
import { useConfirm } from '../../hooks/useConfirm'
import toast from 'react-hot-toast'

const EMPTY_FORM = { name: '', category: CATEGORIES[0].value }

export default function ListManager() {
  const { user } = useAuthStore()
  const canManage = hasPermission(user, 'can_manage_lists')
  const [lists, setLists] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [confirm, confirmDialog] = useConfirm()

  const load = () => {
    listsApi.list().then(setLists).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('Name required')
    try {
      if (editId) {
        await listsApi.update(editId, { name: form.name })
        toast.success('List updated')
      } else {
        await listsApi.create(form)
        toast.success('List created')
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

  const handleEdit = (list) => {
    setEditId(list.id)
    setForm({ name: list.name, category: list.category })
    setShowForm(true)
  }

  const handleDelete = async (list) => {
    if (!await confirm(`Delete "${list.name}"?`)) return
    try {
      await listsApi.delete(list.id)
      toast.success('List deleted')
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
            <Plus size={15} /> New list
          </Button>
        </div>
      )}

      {/* Add/Edit form */}
      {canManage && showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {editId ? 'Edit list' : 'New list'}
          </h3>
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Want to read, Favourites"
            autoFocus
          />
          {!editId && (
            <Select
              label="Category"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            >
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </Select>
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
      ) : lists.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">No lists yet.</p>
      ) : (
        <div className="space-y-5">
          {CATEGORIES.map((category) => {
            const categoryLists = lists
              .filter((l) => l.category === category.value)
              .sort((a, b) => a.name.localeCompare(b.name))
            if (categoryLists.length === 0) return null
            return (
              <div key={category.value} className="space-y-1">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{categoryLabel(category.value)}</h3>
                {categoryLists.map((list) => (
                  <div key={list.id} className="flex items-center gap-3 py-1.5">
                    <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{list.name}</span>
                    <span className="text-xs text-gray-400">{list.item_count} items</span>
                    {canManage && (
                      <>
                        <button
                          onClick={() => handleEdit(list)}
                          className="p-1 rounded-sm text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          onClick={() => handleDelete(list)}
                          className="p-1 rounded-sm text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
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
      )}

      {confirmDialog}
    </div>
  )
}
