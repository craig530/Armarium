import { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import OfflineBanner from '../ui/OfflineBanner'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { mediaApi } from '../../api/media'

export default function Layout() {
  useKeyboardShortcuts()
  const location = useLocation()
  const [stats, setStats] = useState(null)

  // Refetch on every navigation (location.key changes even for same-path
  // clicks) so nav counts and the Home view stay in sync after add/delete.
  useEffect(() => {
    mediaApi.stats().then(setStats).catch(() => {})
  }, [location.key])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      <Navbar stats={stats} />
      <OfflineBanner />
      <main className="mx-auto max-w-7xl px-4 py-6 flex-1 w-full">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
