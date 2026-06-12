import { useNavigate, useLocation } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useAuthStore, hasPermission } from '../../store'

// Floating "Add Item" button shown on mobile only, replacing the navbar's
// Add Item button (hidden below sm:). Sits above the bottom tab bar.
export default function Fab() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()

  if (!hasPermission(user, 'can_add_items')) return null
  if (location.pathname === '/add') return null

  return (
    <button
      onClick={() => navigate('/add')}
      aria-label="Add item"
      className="sm:hidden fixed z-40 right-4 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] h-14 w-14 rounded-full bg-brand-600 text-white shadow-lg flex items-center justify-center active:bg-brand-700 transition-colors"
    >
      <Plus size={26} />
    </button>
  )
}
