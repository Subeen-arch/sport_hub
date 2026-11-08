import { startTransition, useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { errorMessage } from '@/lib/api'
import { AuthContext } from './auth-context'
import { authService, type User } from './auth-service'

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    authService.currentUser()
      .then((current) => { if (active) setUser(current) })
      .catch((reason: unknown) => { if (active) setError(errorMessage(reason)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt])

  return (
    <AuthContext.Provider value={{
      user, loading, error,
      retry: () => { setError(''); setLoading(true); setAttempt((value) => value + 1) },
      login: async (input) => { const current = await authService.login(input); setUser(current); return current },
      register: async (input) => { const current = await authService.register(input); setUser(current); return current },
      // Commit the public destination and cleared session together; otherwise
      // the protected route can redirect to sign-in during logout.
      logout: async () => {
        await authService.logout()
        startTransition(() => { navigate('/', { replace: true }); setUser(null) })
      },
      updateProfile: async (input) => { const current = await authService.updateProfile(input); setUser(current); return current },
    }}>
      {children}
    </AuthContext.Provider>
  )
}
