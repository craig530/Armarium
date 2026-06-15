import { useState } from 'react'
import { Check } from 'lucide-react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import { listsApi } from '../../api/lists'
import { useReferenceDataStore } from '../../store'
import { categoryLabel } from '../../lib/categories'
import toast from 'react-hot-toast'

// Second step of the "List" AddFlow branch — names and creates the new
// ItemList, then hands off to ListItemsStep to populate it.
export default function ListNameStep({ category, onBack, onCreated }) {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const invalidate = useReferenceDataStore((s) => s.invalidate)

  const handleCreate = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    setSaving(true)
    try {
      const created = await listsApi.create({ name: trimmed, category })
      invalidate()
      toast.success(`List "${created.name}" created`)
      onCreated(created)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          New {categoryLabel(category)} list
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Give your list a name, e.g. &quot;Want to read&quot; or &quot;Favourites&quot;.
        </p>
      </div>

      <Input
        label="List name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="e.g. Want to read"
        autoFocus
        onKeyDown={(e) => { if (e.key === 'Enter') handleCreate() }}
      />

      <div className="flex gap-2">
        <Button variant="ghost" onClick={onBack}>Back</Button>
        <Button onClick={handleCreate} loading={saving} disabled={!name.trim()}>
          <Check size={14} /> Create
        </Button>
      </div>
    </div>
  )
}
