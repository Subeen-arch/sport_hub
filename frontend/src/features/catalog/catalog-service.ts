import { apiClient, type ApiTransport, type Paginated } from '@/lib/api'

export type Category = { id: number; name: string }
export type Product = {
  id: number; name: string; category: number; category_name: string; brand: string; details: string
  original_price: string; discount_percent: number; price: string; quantity: number; featured: boolean
  image: string; stock_status: 'in_stock' | 'low_stock' | 'out_of_stock'; created_at: string; updated_at: string
}

export class CatalogService {
  private readonly client: ApiTransport
  constructor(client: ApiTransport = apiClient) { this.client = client }

  products(query = '', signal?: AbortSignal, staff = false): Promise<Paginated<Product>> {
    return this.client.request(`/${staff ? 'admin/' : ''}products/${query ? `?${query}` : ''}`, { signal })
  }

  product(id: string, signal?: AbortSignal, staff = false): Promise<Product> {
    return this.client.request(`/${staff ? 'admin/' : ''}products/${encodeURIComponent(id)}/`, { signal })
  }

  async categories(signal?: AbortSignal): Promise<Category[]> {
    const items: Category[] = []
    let page = 1
    while (true) {
      const response = await this.client.request<Paginated<Category>>(`/categories/?page=${page}`, { signal })
      items.push(...response.results)
      if (!response.next) return items
      page += 1
    }
  }

  options(signal?: AbortSignal): Promise<{ brands: string[] }> {
    return this.client.request('/catalog/options/', { signal })
  }

  saveProduct(data: FormData, id?: number): Promise<Product> {
    return this.client.request(`/admin/products/${id ? `${id}/` : ''}`, { method: id ? 'PATCH' : 'POST', body: data })
  }

  deleteProduct(id: number): Promise<void> {
    return this.client.request(`/admin/products/${id}/`, { method: 'DELETE' })
  }

  saveCategory(name: string, id?: number): Promise<Category> {
    return this.client.request(`/admin/categories/${id ? `${id}/` : ''}`, { method: id ? 'PATCH' : 'POST', body: { name } })
  }

  deleteCategory(id: number): Promise<void> {
    return this.client.request(`/admin/categories/${id}/`, { method: 'DELETE' })
  }
}

export const catalogService = new CatalogService()
