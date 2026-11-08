import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ResourceState } from '@/components/ResourceState'
import { useResource } from '@/lib/use-resource'
import { money } from '@/lib/format'
import { commerceService, type Order } from './commerce-service'

export function OrderSummary({ order }: { order: Order }) {
  return <article className="page-panel space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-xl font-bold">Order #{order.id}</h2><p className="mt-1 break-all text-xs text-muted-foreground">Reference: {order.reference}</p><p className="mt-2 text-sm text-muted-foreground">{new Date(order.created_at).toLocaleString('en-NP', { timeZone: 'Asia/Kathmandu' })}</p></div><p className="text-xl font-bold">{money(order.total)}</p></div>
    <div className="flex flex-wrap gap-3 text-sm"><span className="rounded-full bg-secondary px-3 py-1">Fulfillment: {order.fulfillment_status}</span><span className="rounded-full bg-secondary px-3 py-1">Payment: {order.payment_status}</span><span className="px-3 py-1">{order.method === 'cod' ? 'Cash on delivery' : 'Khalti'}</span></div>
    <ul className="space-y-4">{order.items.map((item) => <li key={item.id} className="flex gap-4 border-t pt-4">{item.image && <img src={item.image} alt="" className="size-16 shrink-0 object-contain" />}<div className="min-w-0 flex-1"><p className="break-words font-semibold">{item.name}</p><p className="text-sm text-muted-foreground">{item.quantity} × {money(item.unit_price)}</p><p>{money(item.subtotal)}</p></div></li>)}</ul>
    <div className="border-t pt-4 text-sm leading-7"><h3 className="font-semibold">Delivery to {order.name}</h3><p>{[order.flat, order.street, order.city, order.region, order.postal_code, order.country].join(', ')}</p><p className="break-words">{order.country_code} {order.phone} · {order.email}</p></div>
    {order.transaction_id && <p className="break-all text-sm">Transaction: {order.transaction_id}</p>}{order.payment_ref && <p className="break-all text-sm">Payment reference: {order.payment_ref}</p>}
  </article>
}

export function OrdersPage() {
  const [page, setPage] = useState(1)
  const resource = useResource(String(page), useCallback((signal) => commerceService.orders(page, signal), [page]))
  return <section className="space-y-6"><h1 className="page-title">Your orders</h1><ResourceState {...resource} />{resource.data && <>{resource.data.results.length ? resource.data.results.map((order) => <div key={order.id} className="space-y-2"><OrderSummary order={order} /><Link to={`/orders/${order.id}`} className="text-sm text-primary hover:underline">View order #{order.id}</Link></div>) : <p className="page-panel">You have no orders yet. <Link to="/shop" className="text-primary underline">Browse the shop</Link>.</p>}<nav aria-label="Order pages" className="flex items-center justify-center gap-4"><Button variant="outline" disabled={!resource.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!resource.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav></>}</section>
}

export function OrderPage() {
  const { id = '' } = useParams()
  const resource = useResource(id, useCallback((signal) => commerceService.order(id, signal), [id]))
  return <section className="mx-auto max-w-3xl space-y-6"><h1 className="page-title">Order details</h1><Link to="/orders" className="text-primary hover:underline">All your orders</Link><ResourceState {...resource} />{resource.data && <OrderSummary order={resource.data} />}</section>
}
