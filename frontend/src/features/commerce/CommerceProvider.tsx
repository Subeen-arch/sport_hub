import { useCallback, type ReactNode } from 'react'
import { useAuth } from '@/features/auth/auth-context'
import { useResource } from '@/lib/use-resource'
import { CommerceContext } from './commerce-context'
import { commerceService } from './commerce-service'

export function CommerceProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const userId = user?.id
  const resource = useResource(String(userId), useCallback(async (signal) => {
    if (!userId) return { cart: { items: [], count: 0, total: '0.00' }, wishlist: { items: [], count: 0 } }
    const [cart, wishlist] = await Promise.all([commerceService.cart(signal), commerceService.wishlist(signal)])
    return { cart, wishlist }
  }, [userId]))
  return <CommerceContext.Provider value={resource}>{children}</CommerceContext.Provider>
}
