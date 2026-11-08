import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Heart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice } from '@/components/FormField'
import { useAuth } from '@/features/auth/auth-context'
import type { Product } from '@/features/catalog/catalog-service'
import { errorMessage } from '@/lib/api'
import { useCommerce } from './commerce-context'
import { commerceService } from './commerce-service'

export function ProductActions({ product, onAdded }: { product: Product; onAdded?: () => void }) {
  const { user } = useAuth()
  const basket = useCommerce()
  const navigate = useNavigate()
  const location = useLocation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inCart = basket.data?.cart.items.some((item) => item.product.id === product.id)
  const inWishlist = basket.data?.wishlist.items.some((item) => item.product.id === product.id)

  async function add(kind: 'cart' | 'wishlist', quantity = 1) {
    if (!user) { navigate('/login', { state: { from: location.pathname + location.search } }); return }
    setBusy(true); setError(''); setSuccess('')
    try {
      if (kind === 'cart') await commerceService.addCart(product.id, quantity)
      else await commerceService.addWishlist(product.id)
      basket.reload(); setSuccess(kind === 'cart' ? 'Added to cart.' : 'Saved to wishlist.'); onAdded?.()
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void add('cart', Number(new FormData(event.currentTarget).get('quantity')))
  }
  return <div className="space-y-3 pt-2">
    <FormNotice error={error} success={success} />
    {inCart ? <Button asChild variant="outline" className="w-full"><Link to="/cart">View cart</Link></Button> : <form onSubmit={submit} className="flex flex-wrap items-end gap-2"><div className="w-20"><FormField label="Quantity" name="quantity" aria-label={`Quantity for ${product.name}`} type="number" min="1" max={Math.max(1, product.quantity)} step="1" defaultValue="1" required disabled={busy || !product.quantity} /></div><Button type="submit" disabled={busy || !product.quantity} className="flex-1">{busy ? 'Adding…' : 'Add to cart'}</Button></form>}
    <Button type="button" variant="ghost" className="w-full" disabled={busy || inCart || inWishlist} onClick={() => add('wishlist')}><Heart aria-hidden="true" />{inWishlist ? 'Saved to wishlist' : 'Save to wishlist'}</Button>
  </div>
}
