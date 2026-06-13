import { NavLink, useNavigate } from 'react-router-dom'
import { Sun, Moon, Plus, LayoutGrid, Music, Clapperboard, BookOpen, Settings, ShieldCheck, LogOut, User, Download, ChevronDown, MapPin, Tv, Tags, Cast } from 'lucide-react'
import { useThemeStore, useAuthStore, hasPermission } from '../../store'
import { useState } from 'react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { CATEGORIES } from '../../lib/categories'
import { exportLibrary } from '../../lib/export'
import Logo from '../ui/Logo'

const CATEGORY_ICONS = {
  music: Music,
  films_tv: Clapperboard,
  books: BookOpen,
}

const navItems = [
  { to: '/', label: 'All', icon: LayoutGrid, end: true },
  ...CATEGORIES.map((c) => ({
    to: `/library/${c.slug}`,
    label: c.label,
    icon: CATEGORY_ICONS[c.value],
    value: c.value,
  })),
]

export const MANAGE_LINKS = [
  { to: '/settings/locations', label: 'Manage Locations', icon: MapPin },
  { to: '/settings/platforms', label: 'Manage Platforms', icon: Tv },
  { to: '/settings/media-subtypes', label: 'Manage Media Types', icon: Tags },
  { to: '/settings/plex', label: 'Plex Sync', icon: Cast },
]

export default function Navbar({ stats }) {
  const { dark, toggle } = useThemeStore()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [manageMenuOpen, setManageMenuOpen] = useState(false)

  const handleExport = async (format) => {
    try {
      const ext = await exportLibrary(format)
      toast.success(`Library exported as ${ext.toUpperCase()}`)
    } catch (err) {
      toast.error(err.message)
    }
    setUserMenuOpen(false)
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-white/90 dark:bg-gray-950/90 backdrop-blur-md border-gray-200 dark:border-gray-800 pt-[env(safe-area-inset-top)]">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-4">
        {/* Logo */}
        <NavLink to="/" end className="flex items-center shrink-0">
          <Logo size={28} withWordmark wordmarkClassName="hidden sm:inline-flex" />
        </NavLink>

        {/* Nav links — hidden on mobile, where the bottom tab bar covers All/Music/Films & TV/Books */}
        <nav className="hidden sm:flex items-center gap-1 ml-2">
          {navItems.map(({ to, label, icon: Icon, end, value }) => {
            const count = value ? stats?.by_category?.[value] : undefined
            return (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300'
                      : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                  )
                }
              >
                <Icon size={15} />
                <span className="hidden sm:block">
                  {label}
                  {typeof count === 'number' ? ` (${count})` : ''}
                </span>
              </NavLink>
            )
          })}
        </nav>

        {/* Manage menu — hidden on mobile, where it's reached via the Profile tab */}
        <div className="relative hidden sm:block">
          <button
            onClick={() => setManageMenuOpen((o) => !o)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              manageMenuOpen
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300'
                : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
            )}
          >
            <Settings size={15} />
            <span className="hidden sm:flex items-center gap-1">
              Manage <ChevronDown size={14} />
            </span>
          </button>

          {manageMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setManageMenuOpen(false)} />
              <div className="absolute left-0 top-full mt-1 z-20 w-52 rounded-xl bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700 py-1 overflow-hidden">
                {MANAGE_LINKS.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setManageMenuOpen(false)}
                    className={({ isActive }) =>
                      clsx(
                        'flex items-center gap-2 px-3 py-2 text-sm',
                        isActive
                          ? 'text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-950'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                      )
                    }
                  >
                    <Icon size={14} /> {label}
                  </NavLink>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Keyboard hint */}
          <span className="hidden lg:flex items-center gap-1 text-xs text-gray-400 mr-1">
            <kbd className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono">/</kbd> search
            <span className="mx-1">·</span>
            <kbd className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono">n</kbd> add
          </span>

          {/* Dark mode toggle */}
          <button
            onClick={toggle}
            className="h-11 w-11 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Toggle theme"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Add item — hidden on mobile, where the FAB covers it */}
          {hasPermission(user, 'can_add_items') && (
            <button
              onClick={() => navigate('/add')}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
            >
              <Plus size={16} />
              <span className="hidden sm:block">Add Item</span>
            </button>
          )}

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen((o) => !o)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 min-h-[44px] rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm"
            >
              <User size={15} />
              <span className="hidden sm:block max-w-[80px] truncate">{user?.username}</span>
              {user?.is_admin && <ShieldCheck size={13} className="text-brand-500 shrink-0" />}
            </button>

            {userMenuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 z-20 w-48 rounded-xl bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700 py-1 overflow-hidden">
                  <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.username}</p>
                    {user?.is_admin && <p className="text-xs text-brand-500">Administrator</p>}
                  </div>

                  <NavLink
                    to="/profile"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <Settings size={14} /> Settings
                  </NavLink>

                  {user?.is_admin && (
                    <NavLink
                      to="/admin"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <ShieldCheck size={14} /> Admin panel
                    </NavLink>
                  )}

                  <button
                    onClick={() => handleExport('csv')}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-left"
                  >
                    <Download size={14} /> Export CSV
                  </button>
                  <button
                    onClick={() => handleExport('json')}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-left"
                  >
                    <Download size={14} /> Export JSON
                  </button>

                  <div className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1">
                    <button
                      onClick={() => { logout(); navigate('/login') }}
                      className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 text-left"
                    >
                      <LogOut size={14} /> Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
