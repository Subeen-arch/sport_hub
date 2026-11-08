import { ApiError, apiClient, type ApiTransport } from '@/lib/api'

export type User = {
  id: number
  username: string
  name: string
  email: string
  phone: string
  country_code: '+977' | '+91'
  is_staff: boolean
}

export type Registration = Pick<User, 'name' | 'email' | 'phone' | 'country_code'> & {
  password: string
  password_confirm: string
}
export type Credentials = { email: string; password: string } | { username: string; password: string }
export type ProfileChanges = Partial<Pick<User, 'name' | 'email' | 'phone' | 'country_code' | 'username'>>
export type PasswordChange = { old_password: string; new_password: string; password_confirm: string }

export class AuthService {
  private readonly client: ApiTransport

  constructor(client: ApiTransport = apiClient) {
    this.client = client
  }

  async currentUser(): Promise<User | null> {
    try {
      return await this.client.request<User>('/auth/me/', { cache: 'no-store' })
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) return null
      throw error
    }
  }

  register(input: Registration): Promise<User> {
    return this.client.request('/auth/register/', { method: 'POST', body: input })
  }

  login(input: Credentials): Promise<User> {
    return this.client.request('/auth/login/', { method: 'POST', body: input })
  }

  logout(): Promise<void> {
    return this.client.request('/auth/logout/', { method: 'POST', body: {} })
  }

  updateProfile(input: ProfileChanges): Promise<User> {
    return this.client.request('/auth/profile/', { method: 'PATCH', body: input })
  }

  changePassword(input: PasswordChange): Promise<{ detail: string }> {
    return this.client.request('/auth/password/', { method: 'POST', body: input })
  }

  staffSession(): Promise<User> {
    return this.client.request('/admin/session/', { cache: 'no-store' })
  }
}

export const authService = new AuthService()
