import { NavLink, useNavigate } from 'react-router-dom'
import { Sun, Moon, SunMoon, Plus, LayoutGrid, Settings, ShieldCheck, LogOut, User, Download } from 'lucide-react'
import { useThemeStore, useAuthStore, hasPermission, useReferenceDataStore } from '../../store'
import { useState } from 'react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { CATEGORIES } from '../../lib/categories'
import { CATEGORY_ICONS } from '../../lib/mediaIcons'
import { exportLibrary } from '../../lib/export'
import Logo from '../ui/Logo'

export default function Navbar() {
  const { dark, preference, toggle } = useThemeStore()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  // Null, or the format currently exporting — large libraries can take a
  // while to generate, so the menu stays open with a spinner rather than
  // giving no feedback while the request is in flight.
  const [exportingFormat, setExportingFormat] = useState(null)
  const appConfig = useReferenceDataStore((s) => s.appConfig)
  const disabledCategories = appConfig?.disabled_categories ?? []

  const navItems = [
    { to: '/', label: 'All', icon: LayoutGrid, end: true },
    ...CATEGORIES
      .filter((c) => !disabledCategories.includes(c.value))
      .map((c) => ({ to: `/library/${c.slug}`, label: c.label, icon: CATEGORY_ICONS[c.value], value: c.value })),
  ]

  const handleExport = async (format) => {
    setExportingFormat(format)
    try {
      const ext = await exportLibrary(format)
      toast.success(`Library exported as ${ext.toUpperCase()}`)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setExportingFormat(null)
      setUserMenuOpen(false)
    }
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
          {navItems.map(({ to, label, icon: Icon, end }) => (
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
              <span className="hidden sm:block">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {/* Keyboard hint */}
          <span className="hidden lg:flex items-center gap-1 text-xs text-gray-400 mr-1">
            <kbd className="px-1.5 py-0.5 rounded-sm bg-gray-100 dark:bg-gray-800 font-mono">/</kbd> search
            <span className="mx-1">·</span>
            <kbd className="px-1.5 py-0.5 rounded-sm bg-gray-100 dark:bg-gray-800 font-mono">n</kbd> add
          </span>

          {/* Theme toggle — icon reflects the current state (not what clicking
              would switch to): auto shows a combined sun/moon glyph, otherwise
              whichever of light/dark is actually active. */}
          <button
            onClick={toggle}
            className="h-11 w-11 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label={`Theme: ${preference === 'auto' ? 'Auto' : dark ? 'Dark' : 'Light'}`}
            title={`Theme: ${preference === 'auto' ? 'Auto' : dark ? 'Dark' : 'Light'}`}
          >
            {preference === 'auto' ? <SunMoon size={18} /> : dark ? <Moon size={18} /> : <Sun size={18} />}
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
              <span className="hidden sm:block max-w-[80px] truncate">{user?.display_name || user?.username}</span>
              {user?.is_admin && <ShieldCheck size={13} className="text-brand-500 shrink-0" />}
            </button>

            {userMenuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 z-20 w-48 rounded-xl bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700 py-1 overflow-hidden">
                  <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.display_name || user?.username}</p>
                    {user?.display_name && <p className="text-xs text-gray-400">@{user?.username}</p>}
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
                    disabled={exportingFormat !== null}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {exportingFormat === 'csv' ? (
                      <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    ) : <Download size={14} />}
                    {exportingFormat === 'csv' ? 'Exporting…' : 'Export CSV'}
                  </button>
                  <button
                    onClick={() => handleExport('json')}
                    disabled={exportingFormat !== null}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {exportingFormat === 'json' ? (
                      <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    ) : <Download size={14} />}
                    {exportingFormat === 'json' ? 'Exporting…' : 'Export JSON'}
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
