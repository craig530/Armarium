import { useState, useEffect } from 'react'
import { Check, Plus } from 'lucide-react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import LoadingSpinner from '../ui/LoadingSpinner'
import { mediaApi } from '../../api/media'
import toast from 'react-hot-toast'

// Final step of the "List" AddFlow branch — search the library (within the
// new list's category) and toggle items in/out of it. Loads with an empty
// query on mount so the user sees something to add immediately, then
// debounces further searches the same way ItemDetail's LinkSearch does.
export default function ListItemsStep({ list, onBack, onDone }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [togglingId, setTogglingId] = useState(null)

  useEffect(() => {
    setLoading(true)
    const handle = setTimeout(() => {
      mediaApi.list({ category: list.category, q: query, per_page: 20 })
        .then((r) => setResults(r.items))
        .catch(() => {})
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(handle)
  }, [query, list.category])

  const handleToggle = async (item) => {
    const inList = item.list_ids.includes(list.id)
    const nextIds = inList
      ? item.list_ids.filter((id) => id !== list.id)
      : [...item.list_ids, list.id]
    setTogglingId(item.id)
    try {
      const updated = await mediaApi.update(item.id, { list_ids: nextIds })
      setResults((items) => items.map((i) => (i.id === updated.id ? updated : i)))
    } catch (err) {
      toast.error(err.message)
    } finally {
      setTogglingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          Add items to &quot;{list.name}&quot;
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Search your library and add items to this list. You can change this anytime.
        </p>
      </div>

      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search your library…"
        autoFocus
      />

      {loading ? (
        <LoadingSpinner size="lg" className="py-8" />
      ) : results.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No items found.</p>
      ) : (
        <ul className="flex flex-col gap-2 max-h-80 overflow-y-auto">
          {results.map((item) => {
            const inList = item.list_ids.includes(list.id)
            const creator = item.artist || item.director || item.author
            return (
              <li key={item.id} className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-2.5">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{item.title}</p>
                  {creator && <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{creator}</p>}
                </div>
                <Button
                  size="sm"
                  variant={inList ? 'secondary' : 'outline'}
                  onClick={() => handleToggle(item)}
                  loading={togglingId === item.id}
                >
                  {inList ? <><Check size={14} /> Added</> : <><Plus size={14} /> Add</>}
                </Button>
              </li>
            )
          })}
        </ul>
      )}

      <div className="flex gap-2">
        <Button variant="ghost" onClick={onBack}>Back</Button>
        <Button onClick={onDone} className="flex-1">Done</Button>
      </div>
    </div>
  )
}
