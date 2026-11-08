import { useCallback, type FormEvent } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormField, SelectField } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { useResource } from '@/lib/use-resource'
import { catalogService } from './catalog-service'
import { ProductGrid } from './ProductCard'
import { sortOptions } from './catalog-options'

export function ShopPage({ search = false }: { search?: boolean }) {
  const [params, setParams] = useSearchParams()
  const { slug } = useParams()
  const query = new URLSearchParams(params)
  if (slug) query.set('category_name', slug.replaceAll('-', ' '))
  const queryString = query.toString()
  const products = useResource(queryString, useCallback((signal) => catalogService.products(queryString, signal), [queryString]))
  const categories = useResource('categories', useCallback((signal) => catalogService.categories(signal), []))
  const options = useResource('options', useCallback((signal) => catalogService.options(signal), []))

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const next = new URLSearchParams()
    new FormData(event.currentTarget).forEach((value, key) => { if (String(value).trim()) next.set(key, String(value).trim()) })
    setParams(next)
  }

  function movePage(delta: number) {
    const next = new URLSearchParams(params)
    next.set('page', String(Math.max(1, Number(params.get('page') || 1) + delta)))
    setParams(next)
  }

  return <section className="space-y-8">
    <div><p className="eyebrow">Find your game</p><h1 className="page-title mt-3">{slug ? slug.replaceAll('-', ' ') : search ? 'Search products' : 'Shop sports gear'}</h1><p className="text-muted-foreground">Explore equipment for your next practice, match or personal best.</p></div>
    <form key={params.toString()} onSubmit={apply} className="page-panel grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <FormField label="Search" name="search" defaultValue={params.get('search') || ''} placeholder="Product, brand or keyword" maxLength={100} required={search} />
      {!slug && <SelectField label="Category" name="category" defaultValue={params.get('category') || ''}><option value="">All categories</option>{categories.data?.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</SelectField>}
      <SelectField label="Brand" name="brand" defaultValue={params.get('brand') || ''}><option value="">All brands</option>{options.data?.brands.map((brand) => <option key={brand} value={brand}>{brand}</option>)}</SelectField>
      <SelectField label="Availability" name="stock" defaultValue={params.get('stock') || ''}><option value="">All products</option><option value="in_stock">In stock</option><option value="out_of_stock">Out of stock</option></SelectField>
      <FormField label="Minimum price (NPR)" name="min_price" type="number" min="0" step="0.01" defaultValue={params.get('min_price') || ''} />
      <FormField label="Maximum price (NPR)" name="max_price" type="number" min="0" step="0.01" defaultValue={params.get('max_price') || ''} />
      <SelectField label="Sort by" name="ordering" defaultValue={params.get('ordering') || '-id'}>{sortOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</SelectField>
      <div className="flex gap-2"><Button type="submit">Apply filters</Button><Button variant="outline" type="button" onClick={() => setParams({})}>Reset</Button></div>
      {params.get('discounted') && <input type="hidden" name="discounted" value={params.get('discounted')!} />}
    </form>
    <ResourceState {...categories} /><ResourceState {...options} /><ResourceState {...products} />
    {products.data && <><p className="text-sm text-muted-foreground">{products.data.count} products</p><ProductGrid products={products.data.results} />
      <nav aria-label="Product pages" className="flex items-center justify-center gap-4"><Button variant="outline" disabled={!products.data.previous} onClick={() => movePage(-1)}>Previous</Button><span>Page {params.get('page') || 1}</span><Button variant="outline" disabled={!products.data.next} onClick={() => movePage(1)}>Next</Button></nav>
    </>}
    {slug && <Link to="/shop" className="text-primary hover:underline">Browse all categories</Link>}
  </section>
}
