import { apiClient, type ApiTransport, type Paginated } from '@/lib/api'
import type { User } from '@/features/auth/auth-service'
import type { Order, Fulfillment } from '@/features/commerce/commerce-service'

export type Dashboard = { pending_total: string; completed_total: string; order_count: number; product_count: number; customer_count: number; admin_count: number; message_count: number; featured_count: number }
export type StaffInput = { username: string; name: string; email: string; password: string; password_confirm: string }
export type Message = { id: number; name: string; email: string; phone: string; country_code: string; message: string; created_at: string }

export class StaffService {
  private readonly client: ApiTransport
  constructor(client: ApiTransport = apiClient) { this.client = client }
  dashboard(signal?: AbortSignal): Promise<Dashboard> { return this.client.request('/admin/dashboard/', { signal }) }
  orders(page: number, status: string, signal?: AbortSignal): Promise<Paginated<Order>> { return this.client.request(`/admin/orders/?${new URLSearchParams({ page: String(page), ...(status ? { status } : {}) })}`, { signal }) }
  updateOrder(id: number, fulfillment_status: Fulfillment): Promise<Order> { return this.client.request(`/admin/orders/${id}/`, { method: 'PATCH', body: { fulfillment_status } }) }
  people(staff: boolean, page: number, signal?: AbortSignal): Promise<Paginated<User>> { return this.client.request(`/admin/${staff ? 'accounts' : 'users'}/?page=${page}`, { signal }) }
  createStaff(data: StaffInput): Promise<User> { return this.client.request('/admin/accounts/', { method: 'POST', body: data }) }
  messages(page: number, signal?: AbortSignal): Promise<Paginated<Message>> { return this.client.request(`/admin/messages/?page=${page}`, { signal }) }
  remove(kind: 'orders' | 'users' | 'accounts' | 'messages', id: number): Promise<void> { return this.client.request(`/admin/${kind}/${id}/`, { method: 'DELETE' }) }
}

export const staffService = new StaffService()
