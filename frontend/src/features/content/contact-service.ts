import { apiClient, type ApiTransport } from '@/lib/api'

export type ContactInput = { name: string; email: string; phone: string; country_code: string; message: string }

export class ContactService {
  private readonly client: ApiTransport
  constructor(client: ApiTransport = apiClient) { this.client = client }

  submit(data: ContactInput): Promise<ContactInput & { id: number; created_at: string }> {
    return this.client.request('/messages/', { method: 'POST', body: data })
  }
}

export const contactService = new ContactService()
