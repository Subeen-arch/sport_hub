import { apiClient, type ApiTransport, type Paginated } from '@/lib/api'
import type { Product } from '@/features/catalog/catalog-service'

export type CartItem = { id: number; product: Product; quantity: number; subtotal: string }
export type WishlistItem = { id: number; product: Product }
export type Cart = { items: CartItem[]; total: string; count: number }
export type Wishlist = { items: WishlistItem[]; count: number }
export type Delivery = { name: string; email: string; phone: string; country_code: string; flat: string; street: string; city: string; region: string; postal_code: string; country: string }
export type OrderItem = { id: number; product: number | null; name: string; image: string; unit_price: string; quantity: number; subtotal: string }
export type Fulfillment = 'pending' | 'Dispatched' | 'completed'
export type Order = Delivery & { id: number; reference: string; method: 'cod' | 'khalti'; fulfillment_status: Fulfillment; payment_status: 'pending' | 'paid' | 'refunded' | 'partially_refunded'; total: string; currency: string; transaction_id: string; payment_ref: string; created_at: string; items: OrderItem[] }

export class CommerceService {
  private readonly client: ApiTransport
  constructor(client: ApiTransport = apiClient) { this.client = client }
  cart(signal?: AbortSignal): Promise<Cart> { return this.client.request('/cart/', { signal }) }
  wishlist(signal?: AbortSignal): Promise<Wishlist> { return this.client.request('/wishlist/', { signal }) }
  addCart(product_id: number, quantity: number): Promise<CartItem> { return this.client.request('/cart/', { method: 'POST', body: { product_id, quantity } }) }
  updateCart(id: number, quantity: number): Promise<CartItem> { return this.client.request(`/cart/${id}/`, { method: 'PATCH', body: { quantity } }) }
  addWishlist(product_id: number): Promise<WishlistItem> { return this.client.request('/wishlist/', { method: 'POST', body: { product_id } }) }
  remove(kind: 'cart' | 'wishlist', id?: number): Promise<void> { return this.client.request(`/${kind}/${id ? `${id}/` : 'clear/'}`, { method: 'DELETE' }) }
  checkout(data: Delivery & { cart_item_ids: number[] }): Promise<Order> { return this.client.request('/orders/checkout/', { method: 'POST', body: data }) }
  orders(page: number, signal?: AbortSignal): Promise<Paginated<Order>> { return this.client.request(`/orders/?page=${page}`, { signal }) }
  order(id: string, signal?: AbortSignal): Promise<Order> { return this.client.request(`/orders/${encodeURIComponent(id)}/`, { signal }) }
}

export const commerceService = new CommerceService()

// Display totals in integer paisa; the server remains authoritative at checkout.
export function sumMoney(amounts: string[]): string {
  const paisa = amounts.reduce((sum, value) => sum + BigInt(value.replace('.', '')), 0n)
  return `${paisa / 100n}.${String(paisa % 100n).padStart(2, '0')}`
}
