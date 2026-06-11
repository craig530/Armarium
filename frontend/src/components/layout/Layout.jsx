import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import OfflineBanner from '../ui/OfflineBanner'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'

export default function Layout() {
  useKeyboardShortcuts()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      <Navbar />
      <OfflineBanner />
      <main className="mx-auto max-w-7xl px-4 py-6 flex-1 w-full">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
