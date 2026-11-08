import { useCallback, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormNotice, SelectField } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { ConfirmAction } from '@/components/ConfirmAction'
import { OrderSummary } from '@/features/commerce/OrdersPage'
import type { Order, Fulfillment } from '@/features/commerce/commerce-service'
import { useResource } from '@/lib/use-resource'
import { errorMessage } from '@/lib/api'
import { staffService } from './staff-service'

function OrderControls({ order, reload }: { order: Order; reload: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const status = String(new FormData(event.currentTarget).get('status')) as Fulfillment
    setBusy(true); setError('')
    try { await staffService.updateOrder(order.id, status); reload() }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  return <div className="space-y-3 rounded-xl border bg-card p-4"><FormNotice error={error} /><div className="flex flex-wrap items-end gap-4"><form onSubmit={submit} className="flex flex-wrap items-end gap-3"><SelectField label={`Status for order ${order.id}`} name="status" defaultValue={order.fulfillment_status} disabled={busy || order.fulfillment_status === 'completed'}><option value="pending">Pending</option><option value="Dispatched">Dispatched</option><option value="completed">Completed</option></SelectField><Button disabled={busy || order.fulfillment_status === 'completed'} type="submit">Save status</Button></form><ConfirmAction label={`Delete order ${order.id}`} title={`Delete order #${order.id}?`} description="This permanently removes the order record. It does not refund payment or return items to stock." action={async () => { await staffService.remove('orders', order.id); reload() }} /></div><p className="text-xs text-muted-foreground">Mark cash-on-delivery orders completed only after delivery and payment collection. Completed orders cannot be reopened.</p></div>
}

export function StaffOrdersPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const resource = useResource(`${page}:${status}`, useCallback((signal) => staffService.orders(page, status, signal), [page, status]))
  function reload() { setPage(1); resource.reload() }
  return <section className="space-y-6"><Link to="/admin" className="text-primary hover:underline">Staff workspace</Link><h1 className="page-title">Manage orders</h1><div className="max-w-xs"><SelectField label="Filter by fulfillment" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">All orders</option><option value="pending">Pending</option><option value="Dispatched">Dispatched</option><option value="completed">Completed</option></SelectField></div><ResourceState {...resource} />{resource.data && <><p>{resource.data.count} orders</p>{resource.data.results.map((order) => <div key={`${order.id}:${order.fulfillment_status}`} className="space-y-3"><OrderSummary order={order} /><OrderControls order={order} reload={reload} /></div>)}{!resource.data.count && <p className="page-panel">No orders match this filter.</p>}<nav aria-label="Staff order pages" className="flex justify-center gap-4"><Button variant="outline" disabled={!resource.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!resource.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav></>}</section>
}
