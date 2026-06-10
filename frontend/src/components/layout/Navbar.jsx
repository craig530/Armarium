import { NavLink, useNavigate } from 'react-router-dom'
import { Sun, Moon, Plus, MapPin, Library, ShieldCheck, LogOut, User, Download } from 'lucide-react'
import { useThemeStore, useAuthStore } from '../../store'
import { useState } from 'react'
import clsx from 'clsx'
import client from '../../api/client'
import toast from 'react-hot-toast'

const navItems = [
  { to: '/library', label: 'Library', icon: Library },
  { to: '/locations', label: 'Locations', icon: MapPin },
]

export default function Navbar() {
  const { dark, toggle } = useThemeStore()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const handleExport = async (format) => {
    try {
      const resp = await client.get(`/library/export?format=${format}`, { responseType: 'blob' })
      const ext = format === 'json' ? 'json' : 'csv'
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `armarium-export.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Library exported as ${ext.toUpperCase()}`)
    } catch (err) {
      toast.error(err.message)
    }
    setUserMenuOpen(false)
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-white/90 dark:bg-gray-950/90 backdrop-blur-md border-gray-200 dark:border-gray-800">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-4">
        {/* Logo */}
        <NavLink to="/library" className="flex items-center gap-2 shrink-0">
          <span className="text-xl">📦</span>
          <span className="font-bold text-gray-900 dark:text-white tracking-tight hidden sm:block">Armarium</span>
        </NavLink>

        {/* Nav links */}
        <nav className="flex items-center gap-1 ml-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
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
            <kbd className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono">/</kbd> search
            <span className="mx-1">·</span>
            <kbd className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono">n</kbd> add
          </span>

          {/* Dark mode toggle */}
          <button
            onClick={toggle}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Toggle theme"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Add item */}
          <button
            onClick={() => navigate('/add')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Plus size={16} />
            <span className="hidden sm:block">Add Item</span>
          </button>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen((o) => !o)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm"
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
