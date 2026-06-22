import { useState, useEffect } from 'react'
import { WifiOff } from 'lucide-react'

export default function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const on = () => setOffline(false)
    const off = () => setOffline(true)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  if (!offline) return null

  return (
    <div className="fixed top-14 inset-x-0 z-50 flex items-center justify-center gap-2 bg-amber-500 text-white py-1.5 px-4 text-sm">
      <WifiOff size={14} />
      You&apos;re offline, showing cached library data
    </div>
  )
}
