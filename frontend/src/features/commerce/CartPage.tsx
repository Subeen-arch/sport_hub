import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice } from '@/components/FormField'
import { ConfirmAction } from '@/components/ConfirmAction'
import { ResourceState } from '@/components/ResourceState'
import { errorMessage } from '@/lib/api'
import { money } from '@/lib/format'
import { useCommerce } from './commerce-context'
import { commerceService, sumMoney, type CartItem } from './commerce-service'

function CartRow({ item, selected, toggle }: { item: CartItem; selected: boolean; toggle: () => void }) {
  const basket = useCommerce()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const quantity = Number(new FormData(event.currentTarget).get('quantity'))
    setBusy(true); setError('')
    try { await commerceService.updateCart(item.id, quantity); basket.reload() }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  return <article className="page-panel space-y-4">
    <div className="flex items-start gap-4"><input type="checkbox" aria-label={`Select ${item.product.name}`} checked={selected} onChange={toggle} className="mt-2 size-5 shrink-0 accent-primary" /><img src={item.product.image} alt="" className="size-20 shrink-0 object-contain" /><div className="min-w-0"><Link to={`/products/${item.product.id}`} className="break-words font-semibold">{item.product.name}</Link><p className="mt-2 text-sm text-muted-foreground">{money(item.product.price)} each</p><p className="mt-2 font-bold">Subtotal: {money(item.subtotal)}</p></div></div>
    {item.quantity > item.product.quantity && <p role="alert" className="text-sm text-destructive">Only {item.product.quantity} in stock. Update or remove this item before checkout.</p>}
    <FormNotice error={error} />
    <div className="flex flex-wrap items-end gap-3"><form onSubmit={update} className="flex items-end gap-3"><div className="w-24"><FormField label="Quantity" aria-label={`Quantity for ${item.product.name}`} name="quantity" type="number" min="1" max={Math.max(item.quantity, item.product.quantity)} step="1" required defaultValue={item.quantity} disabled={busy} /></div><Button type="submit" variant="outline" disabled={busy}>Update</Button></form><ConfirmAction label="Remove" title={`Remove ${item.product.name}?`} description="This item will be removed from your cart." action={async () => { await commerceService.remove('cart', item.id); basket.reload() }} /></div>
  </article>
}

export function CartPage() {
  const basket = useCommerce()
  const navigate = useNavigate()
  const [selected, setSelected] = useState<number[]>([])
  const items = basket.data?.cart.items || []
  const chosen = items.filter((item) => selected.includes(item.id))
  const allSelected = items.length > 0 && chosen.length === items.length
  return <section className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-3"><h1 className="page-title">Your cart</h1><Link to="/shop" className="text-primary hover:underline">Continue shopping</Link></div><ResourceState {...basket} />
    {basket.data && (items.length ? <><div className="flex flex-wrap items-center justify-between gap-3"><label className="flex items-center gap-3"><input type="checkbox" checked={allSelected} onChange={() => setSelected(allSelected ? [] : items.map((item) => item.id))} className="size-5 accent-primary" />Select all</label><ConfirmAction label="Clear cart" title="Clear your cart?" description="All items will be removed from your cart." action={async () => { await commerceService.remove('cart'); setSelected([]); basket.reload() }} /></div>
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]"><div className="space-y-4">{items.map((item) => <CartRow key={`${item.id}:${item.quantity}`} item={item} selected={selected.includes(item.id)} toggle={() => setSelected((current) => current.includes(item.id) ? current.filter((id) => id !== item.id) : [...current, item.id])} />)}</div><aside className="page-panel h-fit space-y-5"><h2 className="text-xl font-bold">Order summary</h2><p>Cart total: {money(basket.data.cart.total)}</p><p>{chosen.length} items selected</p><p className="text-xl font-bold">{money(sumMoney(chosen.map((item) => item.subtotal)))}</p><Button className="w-full" disabled={!chosen.length || chosen.length > 100} onClick={() => navigate(`/checkout?items=${chosen.map((item) => item.id).join(',')}`)}>Checkout selected items</Button>{chosen.length > 100 && <p className="text-sm text-destructive">Select up to 100 items per order.</p>}</aside></div>
    </> : <div className="page-panel"><p>Your cart is empty.</p><Button asChild className="mt-4"><Link to="/shop">Browse products</Link></Button></div>)}
  </section>
}
