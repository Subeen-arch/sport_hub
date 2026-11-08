import { useCallback, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice, SelectField } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError, errorMessage } from '@/lib/api'
import { useResource } from '@/lib/use-resource'
import { money } from '@/lib/format'
import { useCommerce } from './commerce-context'
import { commerceService, sumMoney } from './commerce-service'
import { checkoutUrl, paymentService } from './payment-service'

export function CheckoutPage() {
  const { user } = useAuth()
  const basket = useCommerce()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [method, setMethod] = useState('cod')
  const [uncertain, setUncertain] = useState(false)
  const sending = useRef(false)
  const intent = useRef({ signature: '', key: '' })
  const config = useResource('payment-config', useCallback((signal) => paymentService.config(signal), []))
  const ids = (params.get('items') || '').split(',').map(Number)
  const valid = ids.length > 0 && ids.length <= 100 && ids.every((id) => Number.isSafeInteger(id) && id > 0) && new Set(ids).size === ids.length
  const selected = basket.data?.cart.items.filter((item) => ids.includes(item.id)) || []
  const complete = valid && selected.length === ids.length

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!complete || sending.current || uncertain) return
    const data = new FormData(event.currentTarget)
    const value = (field: string) => String(data.get(field) || '')
    sending.current = true
    setBusy(true); setError('')
    try {
      const payload = { cart_item_ids: ids, name: value('name'), email: value('email'), phone: value('phone'), country_code: value('country_code'), flat: value('flat'), street: value('street'), city: value('city'), region: value('region'), postal_code: value('postal_code'), country: value('country') }
      if (method === 'khalti') {
        const signature = JSON.stringify(payload)
        if (intent.current.signature !== signature) intent.current = { signature, key: crypto.randomUUID() }
        const payment = await paymentService.initiate({ ...payload, request_key: intent.current.key })
        navigate(`/payments/${payment.id}`, { replace: true })
        const url = checkoutUrl(payment)
        if (url) window.location.assign(url)
      } else {
        const order = await commerceService.checkout(payload)
        basket.reload(); navigate(`/orders/${order.id}`, { replace: true })
      }
    } catch (reason) {
      if (reason instanceof ApiError && typeof reason.errors.payment_id === 'string') {
        navigate(`/payments/${encodeURIComponent(reason.errors.payment_id)}`, { replace: true })
      } else {
        setError(errorMessage(reason))
        if (method === 'khalti' && (!(reason instanceof ApiError) || reason.status >= 500)) setUncertain(true)
      }
    }
    finally { sending.current = false; setBusy(false) }
  }

  return <section className="space-y-6"><h1 className="page-title">Checkout</h1><Link to="/cart" className="text-primary hover:underline">Back to cart</Link><ResourceState {...basket} /><FormNotice error={error} />
    {error && <p className="text-sm text-muted-foreground">If your connection was interrupted, check <Link to={method === 'khalti' ? '/payments' : '/orders'} className="text-primary underline">{method === 'khalti' ? 'your payments' : 'your orders'}</Link> before trying again.</p>}
    {basket.data && (!complete ? <p role="alert" className="page-panel">Select available items in your cart before checking out.</p> : <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <form onSubmit={submit} className="page-panel space-y-6"><h2 className="text-xl font-bold">Delivery details</h2><fieldset disabled={busy || uncertain} className="grid gap-5 sm:grid-cols-2">
        <FormField label="Recipient name" name="name" autoComplete="name" required maxLength={100} defaultValue={user?.name || ''} />
        <FormField label="Email address" name="email" type="email" autoComplete="email" required maxLength={254} defaultValue={user?.email || ''} />
        <SelectField label="Country code" name="country_code" defaultValue={user?.country_code || '+977'}><option value="+977">Nepal (+977)</option><option value="+91">India (+91)</option></SelectField>
        <FormField label="Phone number" name="phone" type="tel" autoComplete="tel-national" required pattern="[0-9]{10}" maxLength={10} defaultValue={user?.phone || ''} />
        <FormField label="House or flat" name="flat" autoComplete="address-line1" required maxLength={100} />
        <FormField label="Street" name="street" autoComplete="address-line2" required maxLength={250} />
        <FormField label="City" name="city" autoComplete="address-level2" required maxLength={100} />
        <FormField label="Province or state" name="region" autoComplete="address-level1" required maxLength={100} />
        <FormField label="Postal code" name="postal_code" autoComplete="postal-code" required maxLength={20} pattern="[A-Za-z0-9][A-Za-z0-9 \-]{0,19}" />
        <FormField label="Country" name="country" autoComplete="country-name" required maxLength={100} defaultValue="Nepal" />
        <div className="space-y-3 sm:col-span-2"><h2 className="text-xl font-bold">Payment</h2>
          <SelectField label="Payment method" name="method" value={method} onChange={(event) => setMethod(event.target.value)}><option value="cod">Cash on delivery</option><option value="khalti" disabled={!config.data?.khalti_enabled}>Khalti{config.data?.environment === 'sandbox' ? ' (sandbox)' : ''}</option></SelectField>
          {config.loading && <p role="status" className="text-sm text-muted-foreground">Checking Khalti availability…</p>}
          {!config.loading && !config.data?.khalti_enabled && <p className="text-sm text-muted-foreground">Khalti is currently unavailable. Cash on delivery is available.</p>}
          {config.error && <Button type="button" variant="outline" onClick={config.reload}>Check payment availability again</Button>}
          <p className="text-sm text-muted-foreground">{method === 'khalti' ? 'Continue to Khalti to pay securely. Your order is placed only after payment is verified.' : 'Pay when your order arrives. Prices and stock are checked again when you place your order.'}</p>
          {method === 'khalti' && config.data?.environment === 'sandbox' && <p className="text-sm font-medium">Sandbox mode: this is a test payment.</p>}
          <p className="font-semibold">Total payable: {money(sumMoney(selected.map((item) => item.subtotal)))}</p><Button type="submit" disabled={busy || uncertain}>{busy ? 'Submitting…' : method === 'khalti' ? 'Pay with Khalti' : 'Place order'}</Button>
        </div>
      </fieldset></form>
      <aside className="page-panel h-fit space-y-5"><h2 className="text-xl font-bold">Selected items</h2>{selected.map((item) => <div key={item.id} className="flex gap-3 border-b pb-4"><img src={item.product.image} alt="" className="size-14 object-contain" /><div className="min-w-0"><p className="break-words font-medium">{item.product.name}</p><p className="text-sm text-muted-foreground">{item.quantity} × {money(item.product.price)}</p><p>{money(item.subtotal)}</p></div></div>)}<p className="text-xl font-bold">Total: {money(sumMoney(selected.map((item) => item.subtotal)))}</p></aside>
    </div>)}
  </section>
}
