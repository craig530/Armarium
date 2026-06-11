import clsx from 'clsx'

const CATEGORY_COLORS = {
  music: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  films_tv: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
  books: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
}

export function MediaSubtypeBadge({ subtype, className }) {
  if (!subtype) return null
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', CATEGORY_COLORS[subtype.category], className)}>
      {subtype.name}
    </span>
  )
}

const OWNERSHIP_LABELS = { physical: 'Physical Only', digital: 'Digital Only', both: 'Both' }
const OWNERSHIP_COLORS = {
  physical: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  digital: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  both: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
}

export function OwnershipBadge({ ownership, className }) {
  return (
    <span className={clsx('inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-full text-xs font-medium', OWNERSHIP_COLORS[ownership], className)}>
      {OWNERSHIP_LABELS[ownership] || ownership}
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
