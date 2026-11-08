import { Link } from 'react-router-dom'
import { ConfirmAction } from '@/components/ConfirmAction'
import { ResourceState } from '@/components/ResourceState'
import { ProductCard } from '@/features/catalog/ProductCard'
import { money } from '@/lib/format'
import { useCommerce } from './commerce-context'
import { commerceService, sumMoney } from './commerce-service'

export function WishlistPage() {
  const basket = useCommerce()
  const items = basket.data?.wishlist.items || []
  return <section className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-3"><h1 className="page-title">Your wishlist</h1><Link to="/shop" className="text-primary hover:underline">Continue shopping</Link></div><ResourceState {...basket} />
    {basket.data && (items.length ? <><div className="flex flex-wrap items-center justify-between gap-3"><p>Total for one of each: {money(sumMoney(items.map((item) => item.product.price)))}</p><ConfirmAction label="Clear wishlist" title="Clear your wishlist?" description="All saved products will be removed." action={async () => { await commerceService.remove('wishlist'); basket.reload() }} /></div><div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{items.map((item) => <div key={item.id} className="flex flex-col gap-3"><ProductCard product={item.product} /><ConfirmAction label={`Remove ${item.product.name}`} title="Remove saved product?" description={item.product.name} action={async () => { await commerceService.remove('wishlist', item.id); basket.reload() }} /></div>)}</div></> : <p className="page-panel">Your wishlist is empty. Save products while browsing the shop.</p>)}
  </section>
}
