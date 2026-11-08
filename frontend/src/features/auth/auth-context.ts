import { createContext, useContext } from 'react'
import type { Credentials, ProfileChanges, Registration, User } from './auth-service'

export type AuthState = {
  user: User | null
  loading: boolean
  error: string
  retry: () => void
  login: (input: Credentials) => Promise<User>
  register: (input: Registration) => Promise<User>
  logout: () => Promise<void>
  updateProfile: (input: ProfileChanges) => Promise<User>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth requires AuthProvider.')
  return context
}
