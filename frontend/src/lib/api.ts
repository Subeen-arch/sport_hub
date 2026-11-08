export type ApiProblem = Record<string, unknown>

export class ApiError extends Error {
  readonly status: number
  readonly errors: ApiProblem

  constructor(status: number, errors: ApiProblem) {
    super(problemMessage(errors))
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
  }
}

function problemMessage(errors: ApiProblem): string {
  if (typeof errors.detail === 'string') return errors.detail
  const messages = Object.entries(errors).flatMap(([field, value]) => {
    const text = Array.isArray(value) ? value.join(' ') : typeof value === 'string' ? value : ''
    return text ? [`${field === 'non_field_errors' ? '' : `${field.replaceAll('_', ' ')}: `}${text}`] : []
  })
  return messages.join(' ') || 'The request could not be completed. Please try again.'
}

export type ApiOptions = Omit<RequestInit, 'body' | 'credentials'> & {
  body?: unknown
}

export interface ApiTransport {
  request<T>(path: string, options?: ApiOptions): Promise<T>
}

export class ApiClient implements ApiTransport {
  private csrfRequest: Promise<string> | undefined
  private readonly fetcher: typeof fetch

  constructor(fetcher: typeof fetch = globalThis.fetch.bind(globalThis)) {
    this.fetcher = fetcher
  }

  async ensureCsrf(): Promise<string> {
    // The cookie is HttpOnly and rotates on login/password change. Fetch a fresh
    // token for each mutation; only coalesce requests currently in flight.
    if (!this.csrfRequest) {
      this.csrfRequest = this.fetcher('/api/auth/csrf/', { credentials: 'same-origin', cache: 'no-store' })
        .then(async (response) => {
          if (!response.ok) throw new ApiError(response.status, { detail: 'Unable to establish a secure session.' })
          const data = (await response.json()) as { csrfToken: string }
          if (!data.csrfToken) throw new Error('The server did not provide a CSRF token.')
          return data.csrfToken
        })
        .finally(() => { this.csrfRequest = undefined })
    }
    return this.csrfRequest
  }

  async request<T>(path: string, options: ApiOptions = {}): Promise<T> {
    const url = new URL(`/api${path}`, 'https://sporthub.invalid')
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('://') || !url.pathname.startsWith('/api/')) {
      throw new Error('API paths must be relative to the same-origin /api endpoint.')
    }
    const method = options.method?.toUpperCase() || 'GET'
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      headers.set('X-CSRFToken', await this.ensureCsrf())
    }

    const isFormData = options.body instanceof FormData
    if (options.body !== undefined && !isFormData) headers.set('Content-Type', 'application/json')
    const response = await this.fetcher(`/api${path}`, {
      ...options,
      method,
      headers,
      credentials: 'same-origin',
      body: options.body === undefined ? undefined : isFormData ? options.body as FormData : JSON.stringify(options.body),
    })
    if (response.status === 204) return undefined as T
    const data: unknown = response.headers.get('content-type')?.includes('application/json')
      ? await response.json()
      : undefined
    if (!response.ok) {
      throw new ApiError(response.status,
        data && typeof data === 'object' && !Array.isArray(data)
          ? data as ApiProblem
          : { detail: `The server returned an error (${response.status}). Please try again.` },
      )
    }
    return data as T
  }
}

export const apiClient = new ApiClient()
export const api = <T>(path: string, options?: ApiOptions) => apiClient.request<T>(path, options)

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof TypeError) return 'Unable to reach SportHub. Check your connection and try again.'
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] }
