import { Search } from 'lucide-react'
import clsx from 'clsx'

// Shared search box used by Library and Home, so height/padding/focus-ring
// and dark-mode tokens stay identical across both filter rows.
export default function SearchInput({ value, onChange, placeholder, className }) {
  return (
    <div className={clsx('relative', className)}>
      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <input
        type="search"
        data-search
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full pl-9 pr-4 py-2 text-base sm:text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  )
}
