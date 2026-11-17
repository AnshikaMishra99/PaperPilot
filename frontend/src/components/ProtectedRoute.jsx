import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute({ children }) {
  const { token, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-pine-600 border-t-transparent" />
          <p className="font-read text-sm text-muted">Checking authentication...</p>
        </div>
      </div>
    )
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}
