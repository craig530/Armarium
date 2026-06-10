import clsx from 'clsx'

const TYPE_COLORS = {
  cd: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  dvd: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  bluray: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
  book: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
}

const TYPE_LABELS = { cd: 'CD', dvd: 'DVD', bluray: 'Blu-ray', book: 'Book' }

export function MediaTypeBadge({ type, className }) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', TYPE_COLORS[type], className)}>
      {TYPE_LABELS[type] || type}
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
