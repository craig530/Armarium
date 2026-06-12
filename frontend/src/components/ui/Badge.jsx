import clsx from 'clsx'
import { getSubtypeIcon, OWNERSHIP_ICONS, OWNERSHIP_LABELS } from '../../lib/mediaIcons'

// "Archive ledger" hues: wine for Music, deep emerald for Films & TV, brass for Books.
const CATEGORY_COLORS = {
  music: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  films_tv: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  books: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
}

export function MediaSubtypeBadge({ subtype, className }) {
  if (!subtype) return null
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', CATEGORY_COLORS[subtype.category], className)}>
      {subtype.name}
    </span>
  )
}

// Small icon chip representing an item's media subtype, used in place of the
// text-based MediaSubtypeBadge where space is tight (cards, list rows, hero).
export function MediaSubtypeIcon({ subtype, className }) {
  if (!subtype) return null
  const Icon = getSubtypeIcon(subtype)
  if (!Icon) return null
  return (
    <span
      title={subtype.name}
      className={clsx('inline-flex items-center justify-center h-6 w-6 rounded-full', CATEGORY_COLORS[subtype.category], className)}
    >
      <Icon size={14} />
    </span>
  )
}

const OWNERSHIP_ICON_COLORS = 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'

// Small icon chip representing whether an item is owned physically,
// digitally, or both (one icon per owned form).
export function OwnershipIcon({ ownership, className }) {
  const forms = ownership === 'both' ? ['physical', 'digital'] : [ownership]
  return (
    <span className="inline-flex items-center gap-1">
      {forms.map((form) => {
        const Icon = OWNERSHIP_ICONS[form]
        if (!Icon) return null
        return (
          <span key={form} title={OWNERSHIP_LABELS[form]} className={clsx('inline-flex items-center justify-center h-6 w-6 rounded-full', OWNERSHIP_ICON_COLORS, className)}>
            <Icon size={14} />
          </span>
        )
      })}
    </span>
  )
}

export default function Badge({ children, color = 'gray', className }) {
  const colors = {
    gray: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    green: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    red: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  }
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', colors[color], className)}>
      {children}
    </span>
  )
}
