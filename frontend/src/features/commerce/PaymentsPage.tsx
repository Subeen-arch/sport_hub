import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormNotice } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { errorMessage } from '@/lib/api'
import { money } from '@/lib/format'
import { useResource } from '@/lib/use-resource'
import { OrderSummary } from './OrdersPage'
import { checkoutUrl, paymentMessage, paymentService, type Payment } from './payment-service'
import { useCommerce } from './commerce-context'

function PaymentReference({ payment }: { payment: Payment }) {
  return <dl className="space-y-2 text-sm">
    <div><dt className="text-muted-foreground">Payment reference</dt><dd className="break-all">{payment.id}</dd></div>
    {payment.pidx && <div><dt className="text-muted-foreground">Khalti reference</dt><dd className="break-all">{payment.pidx}</dd></div>}
    <div><dt className="text-muted-foreground">Amount</dt><dd className="font-semibold">{money((payment.amount_paisa / 100).toFixed(2))}</dd></div>
    {payment.environment === 'sandbox' && <div><dt className="font-semibold">Sandbox payment</dt><dd>This is a test payment.</dd></div>}
  </dl>
}

export function PaymentsPage() {
  const [page, setPage] = useState(1)
  const resource = useResource(String(page), useCallback((signal) => paymentService.list(page, signal), [page]))
  return <section className="mx-auto max-w-3xl space-y-6"><h1 className="page-title">Your payments</h1>
    <p className="text-muted-foreground">Review Khalti attempts here, including payments that have not yet created an order.</p>
    <Button variant="outline" onClick={resource.reload}>Refresh payments</Button><ResourceState {...resource} />
    {resource.data && <>{resource.data.results.length ? resource.data.results.map((payment) => <article key={payment.id} className="page-panel space-y-4">
      <h2 className="text-xl font-bold">{paymentMessage(payment).title}</h2><PaymentReference payment={payment} />
      <Button asChild variant="outline"><Link to={`/payments/${payment.id}`}>View payment</Link></Button>
    </article>) : <p className="page-panel">You have no Khalti payments yet.</p>}
      <nav aria-label="Payment pages" className="flex items-center justify-center gap-4"><Button variant="outline" disabled={!resource.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!resource.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav>
    </>}
  </section>
}

export function PaymentPage({ returning = false }: { returning?: boolean }) {
  const { id } = useParams()
  const [params] = useSearchParams()
  const attempt = returning ? params.get('attempt') : id
  const pidx = returning ? params.get('pidx') : null
  // Callback status/amount/transaction fields are intentionally never trusted.
  const load = useCallback(async (signal: AbortSignal) => {
    if (attempt && !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(attempt)) throw new Error('This payment reference is invalid. Open Your payments to find your attempt.')
    if (pidx !== null && !/^[A-Za-z0-9_-]{1,100}$/.test(pidx)) throw new Error('The payment return link is invalid. Open Your payments to check the result.')
    const payment = attempt ? await paymentService.detail(attempt, signal) : undefined
    if (pidx) {
      if (payment && payment.pidx !== pidx) throw new Error('The return link does not match this payment. Open Your payments to check the result.')
      try { return { payment: await paymentService.verify(pidx, signal), verificationError: '' } }
      catch (error) {
        if (!payment) throw error
        return { payment, verificationError: errorMessage(error) }
      }
    }
    if (!payment) throw new Error('The payment return link is incomplete. Open Your payments to find your attempt.')
    return { payment, verificationError: '' }
  }, [attempt, pidx])
  const resource = useResource(`${attempt || ''}:${pidx || ''}`, load)
  return <section className="mx-auto max-w-3xl space-y-6"><h1 className="page-title">Payment details</h1>
    <Link to="/payments" className="text-primary underline">Your payments</Link><ResourceState {...resource} />
    {resource.data && <PaymentResult key={`${resource.data.payment.id}:${resource.data.payment.status}:${resource.data.verificationError}`} initial={resource.data.payment} initialError={resource.data.verificationError} />}
  </section>
}

function PaymentResult({ initial, initialError }: { initial: Payment; initialError: string }) {
  const [payment, setPayment] = useState(initial)
  const [error, setError] = useState(initialError)
  const [busy, setBusy] = useState(false)
  const basket = useCommerce()
  const reloadBasket = basket.reload
  const orderId = payment.order?.id
  useEffect(() => { if (orderId) reloadBasket() }, [orderId, reloadBasket])
  const message = paymentMessage(payment)
  const url = checkoutUrl(payment)
  async function check() {
    if (busy || !payment.pidx) return
    setBusy(true); setError('')
    try { setPayment(await paymentService.verify(payment.pidx)); basket.reload() }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  return <>
    <article className="page-panel space-y-5"><div role="status"><h2 className="text-2xl font-bold">{message.title}</h2><p className="mt-2 text-muted-foreground">{message.description}</p></div>
      <PaymentReference payment={payment} /><FormNotice error={error} />
      {error && <p className="text-sm">The latest result is unavailable. Do not pay again until your payment has been checked.</p>}
      <div className="flex flex-wrap gap-3">
        {payment.pidx && <Button disabled={busy} onClick={check}>{busy ? 'Checking payment…' : 'Check payment again'}</Button>}
        {url && !error && <Button asChild variant="outline"><a href={url} rel="noreferrer">Continue to Khalti</a></Button>}
        {payment.retry_allowed && !error && <Button asChild variant="outline"><Link to="/cart">Return to cart to retry</Link></Button>}
        {(payment.needs_review || !payment.pidx || error) && <Button asChild variant="outline"><Link to="/contact">Contact support</Link></Button>}
        <Button asChild variant="outline"><Link to="/orders">View orders</Link></Button>
        <Button asChild variant="ghost"><Link to="/shop">Continue shopping</Link></Button>
      </div>
    </article>
    {payment.order && <OrderSummary order={payment.order} />}
  </>
}
