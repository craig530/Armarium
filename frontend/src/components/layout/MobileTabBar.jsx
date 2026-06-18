import { NavLink } from 'react-router-dom'
import { LayoutGrid, Settings } from 'lucide-react'
import clsx from 'clsx'
import { CATEGORIES } from '../../lib/categories'
import { CATEGORY_ICONS } from '../../lib/mediaIcons'
import { useReferenceDataStore } from '../../store'

// Fixed bottom navigation shown on mobile only. Mirrors the desktop navbar's
// category links plus a Settings tab, which also houses Manage/Admin/Export
// (see Profile.jsx) so mobile doesn't need a 6th tab.
export default function MobileTabBar() {
  const appConfig = useReferenceDataStore((s) => s.appConfig)
  const disabledCategories = appConfig?.disabled_categories ?? []

  const tabs = [
    { to: '/', label: 'All', icon: LayoutGrid, end: true },
    ...CATEGORIES
      .filter((c) => !disabledCategories.includes(c.value))
      .map((c) => ({ to: `/library/${c.slug}`, label: c.label, icon: CATEGORY_ICONS[c.value] })),
    { to: '/profile', label: 'Settings', icon: Settings },
  ]

  return (
    <nav className="sm:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 dark:bg-gray-950/95 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 pb-[env(safe-area-inset-bottom)]">
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${tabs.length}, 1fr)` }}>
        {tabs.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex flex-col items-center justify-center gap-0.5 min-h-[56px] px-1 text-[11px] font-medium transition-colors',
                isActive ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'
              )
            }
          >
            <Icon size={20} />
            <span className="truncate max-w-full">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
