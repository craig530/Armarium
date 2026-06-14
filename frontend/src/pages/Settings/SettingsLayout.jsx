import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { MapPin, Tv, Tags } from 'lucide-react'
import clsx from 'clsx'

const TABS = [
  {
    to: '/settings/locations',
    label: 'Locations',
    icon: MapPin,
    title: 'Locations',
    description: 'Where your physical media lives — rooms, shelves, boxes and more.',
  },
  {
    to: '/settings/platforms',
    label: 'Platforms',
    icon: Tv,
    title: 'Platforms',
    description: 'Streaming and digital services for your library, e.g. Netflix, Plex, Spotify.',
  },
  {
    to: '/settings/media-subtypes',
    label: 'Mediums',
    icon: Tags,
    title: 'Mediums',
    description: 'Subtypes within each category and format, e.g. CD, Blu-ray, Streaming Film.',
  },
]

export default function SettingsLayout() {
  const location = useLocation()
  const activeTab = TABS.find((t) => location.pathname.startsWith(t.to)) || TABS[0]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{activeTab.title}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{activeTab.description}</p>
      </div>

      <nav className="flex gap-1 border-b border-gray-200 dark:border-gray-800">
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                isActive
                  ? 'border-brand-600 text-brand-700 dark:text-brand-400'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
              )
            }
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5">
        <Outlet />
      </div>
    </div>
  )
}
