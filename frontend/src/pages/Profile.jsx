import { Link, useNavigate } from 'react-router-dom'
import { Sun, Moon, ShieldCheck, LogOut, Download, User } from 'lucide-react'
import { useAuthStore, useThemeStore } from '../store'
import { MANAGE_LINKS } from '../components/layout/Navbar'
import { exportLibrary } from '../lib/export'
import toast from 'react-hot-toast'

export default function Profile() {
  const { user, logout } = useAuthStore()
  const { dark, toggle } = useThemeStore()
  const navigate = useNavigate()

  const handleExport = async (format) => {
    try {
      const ext = await exportLibrary(format)
      toast.success(`Library exported as ${ext.toUpperCase()}`)
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

      {/* Account */}
      <div className="flex items-center gap-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4">
        <div className="h-12 w-12 shrink-0 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-300 flex items-center justify-center">
          <User size={22} />
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 dark:text-white truncate">{user?.username}</p>
          {user?.is_admin && (
            <p className="text-xs text-brand-500 flex items-center gap-1 mt-0.5">
              <ShieldCheck size={12} /> Administrator
            </p>
          )}
        </div>
      </div>

      {/* Appearance */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Appearance</h2>
        <button
          onClick={toggle}
          className="w-full flex items-center justify-between gap-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4 text-left"
        >
          <span className="flex items-center gap-3 text-sm font-medium text-gray-900 dark:text-white">
            {dark ? <Moon size={18} /> : <Sun size={18} />}
            {dark ? 'Dark mode' : 'Light mode'}
          </span>
          <span className="text-xs text-gray-400">Tap to switch</span>
        </button>
      </section>

      {/* Manage */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Manage</h2>
        <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-800 overflow-hidden">
          {MANAGE_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-3 p-4 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <Icon size={16} className="text-gray-400" /> {label}
            </Link>
          ))}
        </div>
      </section>

      {/* Admin */}
      {user?.is_admin && (
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Administration</h2>
          <Link
            to="/admin"
            className="flex items-center gap-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ShieldCheck size={16} className="text-brand-500" /> Admin panel
          </Link>
        </section>
      )}

      {/* Export */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Export</h2>
        <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-800 overflow-hidden">
          <button
            onClick={() => handleExport('csv')}
            className="w-full flex items-center gap-3 p-4 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800 text-left"
          >
            <Download size={16} className="text-gray-400" /> Export library as CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="w-full flex items-center gap-3 p-4 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800 text-left"
          >
            <Download size={16} className="text-gray-400" /> Export library as JSON
          </button>
        </div>
      </section>

      {/* Sign out */}
      <button
        onClick={() => { logout(); navigate('/login') }}
        className="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 dark:border-red-900/40 p-4 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
      >
        <LogOut size={16} /> Sign out
      </button>
    </div>
  )
}
