import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import clsx from 'clsx'

// Custom-styled dropdown matching LocationPicker's button+panel chrome, for
// plain value/label option lists (optionally grouped under headings) — keeps
// filter controls visually consistent instead of mixing native <select>
// elements with LocationPicker's tree picker.
//
// `groups` is an array of `{ label?, options: [{ value, label }] }`. A group
// without a `label` renders its options with no heading (used for a leading
// "All …" option ahead of the real groups).
export default function SelectMenu({ groups, value, onChange, label, placeholder = 'Select…', className }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  const flat = groups.flatMap((g) => g.options)
  const selected = flat.find((o) => String(o.value) === String(value))

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const choose = (val) => {
    onChange(val)
    setOpen(false)
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
            'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent'
          )}
        >
          {/* Muted when the "All ..." option (value === '') is selected,
              matching LocationPicker's placeholder styling — `!selected`
              would never be true here since that option is itself part of
              `flat`. */}
          <span className={clsx('truncate', !value && 'text-gray-400 dark:text-gray-600')}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronDown size={14} className="shrink-0 text-gray-400" />
        </button>

        {open && (
          <div className="absolute z-20 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg max-h-72 overflow-y-auto py-1">
            {groups.map((g, gi) => (
              <div key={g.label || gi}>
                {g.label && (
                  <p className="px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                    {g.label}
                  </p>
                )}
                {g.options.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => choose(opt.value)}
                    className={clsx(
                      'w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 truncate',
                      String(value) === String(opt.value) && 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300'
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
