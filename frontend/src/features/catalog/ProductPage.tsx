import { useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ResourceState } from '@/components/ResourceState'
import { useResource } from '@/lib/use-resource'
import { money } from '@/lib/format'
import { catalogService } from './catalog-service'
import { StockLabel } from './ProductCard'
import { ProductActions } from '@/features/commerce/ProductActions'

export function ProductPage() {
  const { id = '' } = useParams()
  const resource = useResource(id, useCallback((signal) => catalogService.product(id, signal), [id]))
  const product = resource.data
  return <section className="space-y-6"><Link to="/shop" className="text-sm text-primary hover:underline">← Back to shop</Link><ResourceState {...resource} />
    {product && <div className="grid gap-10 md:grid-cols-2">
      <div className="rounded-2xl border bg-card p-8"><img src={product.image} alt={product.name} className="aspect-square w-full object-contain" /></div>
      <div className="space-y-5 py-6"><Link to={`/shop?category=${product.category}`} className="eyebrow hover:underline">{product.category_name}</Link><h1 className="page-title">{product.name}</h1>{product.brand && <p className="text-muted-foreground">By {product.brand}</p>}<StockLabel product={product} />
        <div className="flex flex-wrap items-center gap-4"><strong className="text-3xl">{money(product.price)}</strong>{product.discount_percent > 0 && <><del className="text-muted-foreground">{money(product.original_price)}</del><span className="rounded-full bg-secondary px-3 py-1 text-sm text-primary">Save {product.discount_percent}%</span></>}</div>
        <p className="whitespace-pre-wrap leading-8 text-muted-foreground">{product.details}</p>
        <ProductActions product={product} />
        <Button asChild variant="outline"><Link to="/contact">Ask about this product</Link></Button>
      </div>
    </div>}
  </section>
}
