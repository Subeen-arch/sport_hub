import { createContext, useContext } from 'react'
import type { Cart, Wishlist } from './commerce-service'

export type BasketState = { data?: { cart: Cart; wishlist: Wishlist }; loading: boolean; error?: string; reload: () => void }
export const CommerceContext = createContext<BasketState | null>(null)
export function useCommerce() {
  const context = useContext(CommerceContext)
  if (!context) throw new Error('useCommerce requires CommerceProvider')
  return context
}
