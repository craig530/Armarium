import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store'

export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && !user?.is_admin) {
    return <Navigate to="/library" replace />
  }

  return children
}
