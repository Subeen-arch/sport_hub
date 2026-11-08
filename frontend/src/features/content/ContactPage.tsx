import { useState, type FormEvent } from 'react'
import { FormField, FormNotice, SelectField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/features/auth/auth-context'
import { errorMessage } from '@/lib/api'
import { contactService } from './contact-service'

export function ContactPage() {
  const { user } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setBusy(true); setError(''); setSuccess('')
    try {
      await contactService.submit({ name: String(data.get('name')), email: String(data.get('email')), phone: String(data.get('phone')), country_code: String(data.get('country_code')), message: String(data.get('message')) })
      form.reset()
      setSuccess('Your message has been sent. Thank you for getting in touch.')
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  return <section className="mx-auto max-w-2xl space-y-6">
    <div><p className="eyebrow">Here to help</p><h1 className="page-title mt-3">Contact SportHub</h1><p className="text-muted-foreground">Have a question about our gear? Send our team a message.</p></div>
    <form onSubmit={submit} className="page-panel space-y-5">
      <FormNotice error={error} success={success} />
      <fieldset disabled={busy} className="space-y-5">
        <FormField label="Full name" name="name" autoComplete="name" required maxLength={100} defaultValue={user?.name || ''} />
        <FormField label="Email address" name="email" type="email" autoComplete="email" required maxLength={254} defaultValue={user?.email || ''} />
        <div className="grid gap-4 sm:grid-cols-[140px_1fr]"><SelectField label="Country code" name="country_code" defaultValue={user?.country_code || '+977'}><option value="+977">Nepal (+977)</option><option value="+91">India (+91)</option></SelectField><FormField label="Phone number" name="phone" type="tel" autoComplete="tel-national" pattern="[0-9]{10}" maxLength={10} required defaultValue={user?.phone || ''} help="Enter ten digits." /></div>
        <label className="grid gap-2 text-sm font-medium">Message<Textarea name="message" required maxLength={500} rows={5} /></label>
        <Button type="submit">{busy ? 'Sending…' : 'Send message'}</Button>
      </fieldset>
    </form>
  </section>
}
