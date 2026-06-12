import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore, hasPermission } from '../../store'

export default function ProtectedRoute({ children, requireAdmin = false, requirePermission = null }) {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && !user?.is_admin) {
    return <Navigate to="/library" replace />
  }

  if (requirePermission && !hasPermission(user, requirePermission)) {
    return <Navigate to="/" replace />
  }

  return children
}
