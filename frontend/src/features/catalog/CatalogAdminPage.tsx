import { useCallback, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { FormField, FormNotice, SelectField } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { errorMessage } from '@/lib/api'
import { money } from '@/lib/format'
import { useResource } from '@/lib/use-resource'
import { catalogService, type Category, type Product } from './catalog-service'

function ProductEditor({ product, categories, done, cancel }: { product: Product | null; categories: Category[]; done: () => void; cancel: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    data.set('featured', data.has('featured') ? 'true' : 'false')
    const image = data.get('image')
    if (image instanceof File && !image.size) data.delete('image')
    setBusy(true); setError('')
    try { await catalogService.saveProduct(data, product?.id); done() }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  return <form onSubmit={save} className="page-panel space-y-5" aria-label="Product editor">
    <h2 className="text-xl font-bold">{product ? 'Edit product' : 'New product'}</h2><FormNotice error={error} />
    <fieldset disabled={busy} className="grid gap-5 sm:grid-cols-2">
      <FormField label="Product name" name="name" required maxLength={100} defaultValue={product?.name || ''} />
      <SelectField label="Category" name="category" required defaultValue={product?.category || ''}><option value="" disabled>Select category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</SelectField>
      <FormField label="Brand" name="brand" maxLength={100} defaultValue={product?.brand || ''} />
      <FormField label="Original price (NPR)" name="original_price" type="number" min="0" max="9999999999.99" step="0.01" required defaultValue={product?.original_price || ''} />
      <FormField label="Discount (%)" name="discount_percent" type="number" min="0" max="100" step="1" required defaultValue={product?.discount_percent || 0} />
      <FormField label="Stock quantity" name="quantity" type="number" min="0" max="2147483647" step="1" required defaultValue={product?.quantity || 0} />
      <label className="grid gap-2 text-sm font-medium sm:col-span-2">Description<Textarea name="details" required maxLength={500} rows={4} defaultValue={product?.details || ''} /></label>
      <div className="sm:col-span-2"><FormField label="Product image" name="image" type="file" accept="image/jpeg,image/png,image/webp" required={!product} help="JPEG, PNG or WebP, up to 2 MB. Leave blank to keep the current image when editing." />{product && <img src={product.image} alt="Current product" className="mt-3 size-24 rounded-md border object-contain" />}</div>
      <label className="flex items-center gap-3 text-sm"><input name="featured" type="checkbox" defaultChecked={product?.featured || false} className="size-4 accent-primary" />Featured (up to six products)</label>
      <div className="flex gap-3 sm:col-span-2"><Button type="submit">{busy ? 'Saving…' : 'Save product'}</Button><Button type="button" variant="outline" onClick={cancel}>Cancel</Button></div>
    </fieldset>
  </form>
}

type Deletion = { type: 'product' | 'category'; id: number; name: string }

export function CatalogAdminPage() {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [editor, setEditor] = useState<{ product: Product | null } | null>(null)
  const [categoryEditor, setCategoryEditor] = useState<Category | null>(null)
  const [deletion, setDeletion] = useState<Deletion | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [success, setSuccess] = useState('')
  const categories = useResource('categories', useCallback((signal) => catalogService.categories(signal), []))
  const queryString = new URLSearchParams({ search: query, page: String(page) }).toString()
  const products = useResource(queryString, useCallback((signal) => catalogService.products(queryString, signal, true), [queryString]))

  function refresh(message: string) {
    categories.reload(); products.reload(); setError(''); setSuccess(message)
  }

  async function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const name = String(new FormData(form).get('name'))
    setBusy(true); setError(''); setSuccess('')
    try {
      await catalogService.saveCategory(name, categoryEditor?.id)
      form.reset(); setCategoryEditor(null); refresh('Category saved.')
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  async function remove() {
    if (!deletion) return
    setBusy(true); setDeleteError('')
    try {
      if (deletion.type === 'product') await catalogService.deleteProduct(deletion.id)
      else await catalogService.deleteCategory(deletion.id)
      if (deletion.type === 'product' && editor?.product?.id === deletion.id) setEditor(null)
      if (deletion.type === 'category' && categoryEditor?.id === deletion.id) setCategoryEditor(null)
      setDeletion(null); setPage(1); refresh('Deleted successfully.')
    } catch (reason) { setDeleteError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  function confirmDeletion(item: Deletion) { setDeleteError(''); setDeletion(item) }

  return <section className="space-y-8">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><Link to="/admin" className="text-sm text-primary hover:underline">Staff workspace</Link><h1 className="page-title mt-3">Manage catalog</h1></div><Button onClick={() => { setEditor({ product: null }); setSuccess('') }} disabled={!categories.data?.length}>Add product</Button></div>
    <FormNotice error={error} success={success} />
    <ResourceState {...categories} />
    {editor && categories.data && <ProductEditor key={editor.product?.id || 'new'} product={editor.product} categories={categories.data} done={() => { setEditor(null); setPage(1); refresh('Product saved.') }} cancel={() => setEditor(null)} />}
    <section className="page-panel space-y-5" aria-labelledby="categories-title">
      <h2 id="categories-title" className="text-xl font-bold">Categories</h2>
      <form key={categoryEditor?.id || 'new'} onSubmit={saveCategory} className="flex flex-wrap items-end gap-3">
        <FormField label={categoryEditor ? 'Rename category' : 'New category name'} name="name" maxLength={100} required defaultValue={categoryEditor?.name || ''} disabled={busy} />
        <Button disabled={busy} type="submit">{categoryEditor ? 'Save category' : 'Add category'}</Button>
        {categoryEditor && <Button disabled={busy} variant="outline" type="button" onClick={() => setCategoryEditor(null)}>Cancel rename</Button>}
      </form>
      {categories.data?.length === 0 && <p className="text-muted-foreground">Create a category before adding your first product.</p>}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{categories.data?.map((category) => <li key={category.id} className="flex flex-wrap items-center gap-2 rounded-md border p-3"><span className="min-w-0 flex-1 break-words">{category.name}</span><Button size="sm" variant="outline" aria-label={`Rename ${category.name}`} onClick={() => setCategoryEditor(category)}>Rename</Button><Button size="sm" variant="ghost" aria-label={`Delete category ${category.name}`} onClick={() => confirmDeletion({ type: 'category', ...category })}>Delete</Button></li>)}</ul>
    </section>
    <section className="space-y-5" aria-labelledby="products-title">
      <h2 id="products-title" className="text-xl font-bold">Products</h2>
      <form className="flex flex-wrap items-end gap-3" onSubmit={(event) => { event.preventDefault(); setQuery(String(new FormData(event.currentTarget).get('search'))); setPage(1) }}><FormField label="Search catalog" name="search" maxLength={100} /><Button type="submit" variant="outline">Search</Button></form>
      <ResourceState {...products} />
      {products.data && <><p className="text-sm text-muted-foreground">{products.data.count} products</p><div className="grid gap-4 md:grid-cols-2">{products.data.results.map((product) => <article key={product.id} className="flex gap-4 rounded-xl border bg-card p-4"><img src={product.image} alt="" className="size-20 shrink-0 rounded-md object-contain" /><div className="min-w-0 space-y-2"><h3 className="break-words font-semibold"><Link to={`/products/${product.id}`}>{product.name}</Link></h3><p className="text-sm text-muted-foreground">{money(product.price)} · {product.quantity} in stock{product.featured ? ' · Featured' : ''}</p><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => { setEditor({ product }); setSuccess(''); window.scrollTo({ top: 0, behavior: 'smooth' }) }} aria-label={`Edit ${product.name}`}>Edit</Button><Button size="sm" variant="ghost" onClick={() => confirmDeletion({ type: 'product', ...product })} aria-label={`Delete product ${product.name}`}>Delete</Button></div></div></article>)}</div>
        {products.data.count === 0 && <p className="rounded-xl border border-dashed p-8 text-muted-foreground">No products found. Add a product or try a different search.</p>}
        <nav aria-label="Catalog pages" className="flex items-center justify-center gap-4"><Button variant="outline" disabled={!products.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!products.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav></>}
    </section>
    <AlertDialog open={!!deletion} onOpenChange={(open) => { if (!open && !busy) setDeletion(null) }}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete {deletion?.name}?</AlertDialogTitle><AlertDialogDescription>{deletion?.type === 'category' ? 'Only empty categories can be deleted.' : 'This removes the product from the catalog. Existing order records are preserved.'}</AlertDialogDescription></AlertDialogHeader><FormNotice error={deleteError} /><AlertDialogFooter><AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel><Button variant="destructive" disabled={busy} onClick={remove}>{busy ? 'Deleting…' : 'Delete'}</Button></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </section>
}
