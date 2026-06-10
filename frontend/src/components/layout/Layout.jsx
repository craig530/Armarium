import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import OfflineBanner from '../ui/OfflineBanner'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'

export default function Layout() {
  useKeyboardShortcuts()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Navbar />
      <OfflineBanner />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
