import { Link } from 'react-router-dom'
import { money } from '@/lib/format'
import type { Product } from './catalog-service'
import { ProductActions } from '@/features/commerce/ProductActions'

export function StockLabel({ product }: { product: Product }) {
  return <span className={`text-sm ${product.quantity ? 'text-primary' : 'text-muted-foreground'}`}>{product.quantity === 0 ? 'Out of stock' : product.quantity <= 3 ? `Only ${product.quantity} left` : 'In stock'}</span>
}

export function ProductCard({ product }: { product: Product }) {
  return <article className="group flex h-full flex-col overflow-hidden rounded-xl border bg-card">
    <Link to={`/products/${product.id}`} className="relative block bg-muted p-5" aria-label={`View ${product.name}`}>
      <img src={product.image} alt={product.name} loading="lazy" className="aspect-square w-full object-contain transition-transform group-hover:scale-105" />
      {product.discount_percent > 0 && <span className="absolute left-3 top-3 rounded-full bg-primary px-3 py-1 text-xs font-bold text-white">{product.discount_percent}% off</span>}
    </Link>
    <div className="flex flex-1 flex-col gap-2 p-5">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{product.category_name}{product.brand ? ` · ${product.brand}` : ''}</p>
      <h3 className="font-semibold"><Link to={`/products/${product.id}`} className="hover:text-primary">{product.name}</Link></h3>
      <p className="line-clamp-2 text-sm text-muted-foreground">{product.details}</p>
      <div className="mt-auto flex flex-wrap items-baseline gap-2 pt-3"><span className="font-bold">{money(product.price)}</span>{product.discount_percent > 0 && <del className="text-sm text-muted-foreground">{money(product.original_price)}</del>}</div>
      <StockLabel product={product} />
      <ProductActions product={product} />
    </div>
  </article>
}

export function ProductGrid({ products }: { products: Product[] }) {
  if (!products.length) return <p className="rounded-xl border border-dashed p-10 text-center text-muted-foreground">No products found. Try another search or check back soon.</p>
  return <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div>
}
