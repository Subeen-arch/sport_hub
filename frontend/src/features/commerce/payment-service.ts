import { apiClient, type ApiTransport, type Paginated } from '@/lib/api'
import type { Delivery, Order } from './commerce-service'

export type Payment = {
  id: string; pidx: string | null; environment: 'sandbox' | 'live'
  status: 'Initiated' | 'Pending' | 'Completed' | 'Failed' | 'User canceled' | 'Expired' | 'Refunded' | 'Partially refunded'
  provider_status: string; amount_paisa: number; payment_url: string; expires_at: string | null
  needs_review: boolean; failure_code: string; retry_allowed: boolean; order: Order | null; created_at: string
}

export class PaymentService {
  private readonly client: ApiTransport
  constructor(client: ApiTransport = apiClient) { this.client = client }
  config(signal?: AbortSignal): Promise<{ khalti_enabled: boolean; environment: 'sandbox' | 'live' }> {
    return this.client.request('/payments/config/', { signal })
  }
  initiate(data: Delivery & { cart_item_ids: number[]; request_key: string }): Promise<Payment> {
    return this.client.request('/payments/khalti/initiate/', { method: 'POST', body: data })
  }
  verify(pidx: string, signal?: AbortSignal): Promise<Payment> {
    return this.client.request('/payments/khalti/verify/', { method: 'POST', body: { pidx }, signal })
  }
  list(page: number, signal?: AbortSignal): Promise<Paginated<Payment>> {
    return this.client.request(`/payments/?page=${page}`, { signal })
  }
  detail(id: string, signal?: AbortSignal): Promise<Payment> {
    return this.client.request(`/payments/${encodeURIComponent(id)}/`, { signal })
  }
}

export const paymentService = new PaymentService()

// Defense in depth: redirect only to the provider URL bound to this attempt.
export function checkoutUrl(payment: Payment): string | undefined {
  if (payment.needs_review || payment.status !== 'Initiated' || !payment.pidx || !payment.expires_at || !Number.isFinite(Date.parse(payment.expires_at)) || Date.parse(payment.expires_at) <= Date.now()) return
  try {
    const url = new URL(payment.payment_url)
    const host = payment.environment === 'sandbox' ? 'test-pay.khalti.com' : 'pay.khalti.com'
    if (url.protocol === 'https:' && url.hostname === host && !url.port && !url.username && !url.password && !url.hash && url.searchParams.getAll('pidx').length === 1 && url.searchParams.get('pidx') === payment.pidx) return url.href
  } catch { /* An invalid provider URL never becomes a navigation target. */ }
}

export function paymentMessage(payment: Payment): { title: string; description: string } {
  if (payment.needs_review) return { title: 'Payment needs review', description: 'We could not safely confirm the result. Please contact support with the payment reference below. Do not pay again while this is being resolved.' }
  switch (payment.status) {
    case 'Completed': return payment.order
      ? { title: 'Payment confirmed', description: 'Your Khalti payment is verified and your order has been placed.' }
      : { title: 'Payment recorded', description: 'The order is unavailable. Contact support with your payment reference before paying again.' }
    case 'Pending': return { title: 'Payment pending', description: 'Khalti has not confirmed the payment yet. Check again shortly. Do not start another payment for these items.' }
    case 'Initiated': return { title: 'Payment awaiting confirmation', description: 'Your payment has not been confirmed. You can check its status here after returning from Khalti.' }
    case 'User canceled': return { title: 'Payment canceled', description: 'Khalti confirmed cancellation. Your selected items remain in your cart.' }
    case 'Expired': return { title: 'Payment expired', description: 'Khalti confirmed that this payment expired. Return to your cart to try again.' }
    case 'Refunded': return { title: 'Payment refunded', description: 'Khalti reports a full refund. Contact support if you need help with the refund or an existing order.' }
    case 'Partially refunded': return { title: 'Payment partially refunded', description: 'Contact support to review the remaining payment and your order.' }
    default: return { title: 'Payment could not start', description: 'This payment attempt failed. Your selected items remain in your cart.' }
  }
}
