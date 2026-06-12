import { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import MobileTabBar from './MobileTabBar'
import Fab from './Fab'
import OfflineBanner from '../ui/OfflineBanner'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { mediaApi } from '../../api/media'
import { useAuthStore } from '../../store'

export default function Layout() {
  useKeyboardShortcuts()
  const location = useLocation()
  const [stats, setStats] = useState(null)
  const refreshUser = useAuthStore((s) => s.refreshUser)

  // Refetch on every navigation (location.key changes even for same-path
  // clicks) so nav counts and the Home view stay in sync after add/delete.
  useEffect(() => {
    mediaApi.stats().then(setStats).catch(() => {})
  }, [location.key])

  // Refresh permission flags once on app load so a session started before a
  // permission change picks up the latest values without re-login.
  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      <Navbar stats={stats} />
      <OfflineBanner />
      <main className="mx-auto max-w-7xl px-4 py-6 flex-1 w-full pb-24 sm:pb-6">
        <Outlet />
      </main>
      <Footer />
      <Fab />
      <MobileTabBar />
    </div>
  )
}
