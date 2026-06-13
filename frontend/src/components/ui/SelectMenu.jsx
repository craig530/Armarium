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
//
// `renderIcon(opt)`, if given, renders an icon before each option's label
// (and before the selected option's label in the trigger button) — used to
// show platform logos, matching LocationPicker's inline location icons.
export default function SelectMenu({ groups, value, onChange, label, placeholder = 'Select…', renderIcon, className }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  const flat = groups.flatMap((g) => g.options)
  const selected = flat.find((o) => String(o.value) === String(value))
  // The first option represents the "unset" default for the control —
  // a placeholder like "All locations" for filters, or the initial sort/order
  // value. Muting it keeps untouched controls visually consistent with each
  // other, regardless of whether their default value happens to be ''.
  const isDefault = flat.length > 0 && String(value) === String(flat[0].value)

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
          {/* Muted when the first/default option is selected, matching
              LocationPicker's placeholder styling. */}
          <span className={clsx('truncate flex items-center gap-2 min-w-0', isDefault && 'text-gray-400 dark:text-gray-600')}>
            {selected && renderIcon?.(selected)}
            <span className="truncate">{selected ? selected.label : placeholder}</span>
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
                      'w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 truncate flex items-center gap-2',
                      String(value) === String(opt.value) && 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300'
                    )}
                  >
                    {renderIcon?.(opt)}
                    <span className="truncate">{opt.label}</span>
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
