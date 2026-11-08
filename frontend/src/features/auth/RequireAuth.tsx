import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './auth-context'

export function RequireAuth({ staff = false }: { staff?: boolean }) {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) return <Navigate to={staff ? '/admin/login' : '/login'} state={{ from: location.pathname + location.search }} replace />
  if (staff && !user.is_staff) {
    return <section className="page-panel"><h1 className="page-title">Staff access required</h1><p className="text-muted-foreground">Your account does not have access to this page.</p></section>
  }
  return <Outlet />
}
