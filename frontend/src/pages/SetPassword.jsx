import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useThemeStore } from '../store'
import { Eye, EyeOff, Sun, Moon } from 'lucide-react'
import toast from 'react-hot-toast'
import Logo from '../components/ui/Logo'
import { authApi } from '../api/auth'

export default function SetPassword() {
  const { dark, toggle } = useThemeStore()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [checking, setChecking] = useState(true)
  const [valid, setValid] = useState(false)
  const [form, setForm] = useState({ password: '', confirm: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!token) {
      setChecking(false)
      setValid(false)
      return
    }
    authApi
      .validateResetToken(token)
      .then((r) => setValid(r.valid))
      .catch(() => setValid(false))
      .finally(() => setChecking(false))
  }, [token])

  const error =
    form.password && form.password.length < 8
      ? 'Password must be at least 8 characters'
      : form.confirm && form.password !== form.confirm
        ? 'Passwords do not match'
        : null

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (error || form.password.length < 8) return
    setSubmitting(true)
    try {
      await authApi.resetPassword(token, form.password)
      toast.success('Password set — you can now log in')
      navigate('/login', { replace: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <button
        onClick={toggle}
        className="fixed top-4 right-4 p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        {dark ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Logo size={64} className="mb-3 [&>img]:rounded-2xl justify-center" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Armarium</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">Your personal media catalogue</p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-xl p-8">
          {checking ? (
            <p className="text-sm text-gray-400 animate-pulse">Checking your link…</p>
          ) : !valid ? (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Link expired</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                This link is invalid or has expired. Request a new one below.
              </p>
              <Link
                to="/forgot-password"
                className="inline-block w-full text-center py-2.5 px-4 rounded-lg bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 transition-colors"
              >
                Request a new link
              </Link>
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Set your password</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">New password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      autoFocus
                      value={form.password}
                      onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                      className="w-full rounded-lg border px-3 py-2 pr-10 text-base sm:text-sm bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Confirm password</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={form.confirm}
                    onChange={(e) => setForm((f) => ({ ...f, confirm: e.target.value }))}
                    className="w-full rounded-lg border px-3 py-2 text-base sm:text-sm bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                  />
                  {error && <p className="text-xs text-red-500">{error}</p>}
                </div>

                <button
                  type="submit"
                  disabled={submitting || !!error || form.password.length < 8 || !form.confirm}
                  className="w-full py-2.5 px-4 rounded-lg bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {submitting ? 'Saving…' : 'Set password'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
