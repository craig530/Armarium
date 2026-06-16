import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronDown, Search } from 'lucide-react'
import clsx from 'clsx'
import LocationIcon from '../ui/LocationIcon'
import { flattenLocations, excludeLocationSubtree } from '../../lib/locations'

// Searchable, tree-aware location picker. Every option shows its full
// breadcrumb path (e.g. "Living Room → Bookshelf → Shelf 2") so locations
// with the same name under different parents are never ambiguous, and is
// indented to reflect its depth in the tree. Search matches against the
// full path, not just the leaf name.
export default function LocationPicker({
  locations,
  value,
  onChange,
  label,
  placeholder = 'No location',
  excludeId = null,
  className,
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef(null)

  const flat = useMemo(
    () => excludeLocationSubtree(flattenLocations(locations), excludeId),
    [locations, excludeId]
  )
  const selected = flat.find((l) => String(l.id) === String(value))

  const q = query.trim().toLowerCase()
  const filtered = q ? flat.filter((l) => l.path.toLowerCase().includes(q)) : flat

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const choose = (id) => {
    onChange(id)
    setOpen(false)
    setQuery('')
  }

  return (
    <div className={clsx('flex flex-col gap-1', className)} ref={containerRef}>
      {label && <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>}
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className={clsx(
            // text-base (16px) on mobile prevents iOS Safari's zoom-on-focus, matching Input/Select.
            'w-full flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-base sm:text-sm text-left',
            'bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100',
            'border-gray-300 dark:border-gray-700',
            'focus:outline-hidden focus:ring-2 focus:ring-brand-500 focus:border-transparent'
          )}
        >
          <span
            title={selected ? selected.path : undefined}
            className={clsx('truncate flex items-center gap-2 min-w-0', !selected && 'text-gray-400 dark:text-gray-600')}
          >
            {selected && <LocationIcon location={selected} size={14} className="shrink-0 text-gray-400" />}
            <span className="truncate">{selected ? selected.name : placeholder}</span>
          </span>
          <ChevronDown size={14} className="shrink-0 text-gray-400" />
        </button>

        {open && (
          <div className="absolute z-20 mt-1 min-w-full w-max max-w-[22rem] rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg max-h-72 flex flex-col">
            <div className="p-2 border-b border-gray-100 dark:border-gray-800 shrink-0">
              <div className="relative">
                <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search locations…"
                  className="w-full rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 pl-7 pr-2 py-1.5 text-base sm:text-sm text-gray-900 dark:text-gray-100 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>
            <div className="overflow-y-auto py-1">
              <button
                type="button"
                onClick={() => choose('')}
                className={clsx(
                  'w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800',
                  !value && 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300'
                )}
              >
                {placeholder}
              </button>
              {filtered.length === 0 && (
                <p className="px-3 py-2 text-sm text-gray-400">No locations found</p>
              )}
              {filtered.map((loc) => (
                <button
                  key={loc.id}
                  type="button"
                  onClick={() => choose(String(loc.id))}
                  style={!q ? { paddingLeft: `${0.75 + loc.depth * 1}rem` } : undefined}
                  title={loc.path}
                  className={clsx(
                    'w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 truncate flex items-center gap-2',
                    String(value) === String(loc.id) && 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300'
                  )}
                >
                  <LocationIcon location={loc} size={13} className="shrink-0 text-gray-400" />
                  <span className="truncate">{loc.path}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
