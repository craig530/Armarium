import { useEffect } from 'react'
import clsx from 'clsx'
import { useReferenceDataStore } from '../../store'

// Chip-toggle picker for an item's list memberships, scoped to its category.
// Renders nothing if no lists exist for that category yet (the user hasn't
// created any from Settings → Lists or the AddFlow "List" branch).
export default function ListsMultiSelect({ category, value = [], onChange, label = 'Lists', className }) {
  const { lists, ensureLoaded } = useReferenceDataStore()
  useEffect(() => { ensureLoaded() }, [ensureLoaded])

  const options = lists.filter((l) => l.category === category)
  if (options.length === 0) return null

  const toggle = (id) => {
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id])
  }

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((list) => (
          <button
            key={list.id}
            type="button"
            onClick={() => toggle(list.id)}
            className={clsx(
              'px-3 py-1.5 rounded-full text-sm font-medium border transition-colors',
              value.includes(list.id)
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700'
            )}
          >
            {list.name}
          </button>
        ))}
      </div>
    </div>
  )
}
