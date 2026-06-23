import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useThemeStore } from '../store'
import { Sun, Moon, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import Logo from '../components/ui/Logo'
import { authApi } from '../api/auth'

export default function ForgotPassword() {
  const { dark, toggle } = useThemeStore()
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!value.trim()) return
    setLoading(true)
    try {
      await authApi.forgotPassword(value.trim())
      setSubmitted(true)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
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
          {submitted ? (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Check your email</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                If that account exists and has an email on file, a link to reset your password is on its way.
              </p>
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Forgot password</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Enter your username or email and we&apos;ll send you a link to set a new password.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Username or email</label>
                  <input
                    type="text"
                    autoFocus
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 text-base sm:text-sm bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !value.trim()}
                  className="w-full py-2.5 px-4 rounded-lg bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
            </>
          )}

          <Link
            to="/login"
            className="mt-6 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white"
          >
            <ArrowLeft size={14} /> Back to login
          </Link>
        </div>
      </div>
    </div>
  )
}
