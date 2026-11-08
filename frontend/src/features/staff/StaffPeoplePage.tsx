import { useCallback, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice } from '@/components/FormField'
import { ResourceState } from '@/components/ResourceState'
import { ConfirmAction } from '@/components/ConfirmAction'
import { useAuth } from '@/features/auth/auth-context'
import { useResource } from '@/lib/use-resource'
import { errorMessage } from '@/lib/api'
import { staffService } from './staff-service'

export function StaffPeoplePage({ staff = false }: { staff?: boolean }) {
  const { user } = useAuth()
  const [page, setPage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const resource = useResource(`${staff}:${page}`, useCallback((signal) => staffService.people(staff, page, signal), [staff, page]))
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const value = (key: string) => String(data.get(key) || '')
    setBusy(true); setError(''); setSuccess('')
    try { await staffService.createStaff({ username: value('username'), name: value('name'), email: value('email'), password: value('password'), password_confirm: value('password_confirm') }); form.reset(); setPage(1); resource.reload(); setSuccess('Staff account created.') }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  return <section className="space-y-6"><Link to="/admin" className="text-primary hover:underline">Staff workspace</Link><h1 className="page-title">{staff ? 'Staff accounts' : 'Customers'}</h1><FormNotice error={error} success={success} />
    {staff && <form onSubmit={create} className="page-panel space-y-5"><h2 className="text-xl font-bold">Create staff account</h2><fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2"><FormField label="Staff username" name="username" required maxLength={150} autoComplete="off" /><FormField label="Full name" name="name" required maxLength={100} /><FormField label="Email address" name="email" type="email" required maxLength={254} /><FormField label="Password" name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} help="Use at least eight characters, including a special character." /><FormField label="Confirm password" name="password_confirm" type="password" autoComplete="new-password" required minLength={8} maxLength={128} /><div className="self-end"><Button type="submit">{busy ? 'Creating…' : 'Create staff account'}</Button></div></fieldset></form>}
    <ResourceState {...resource} />{resource.data && <><p>{resource.data.count} {staff ? 'staff accounts' : 'customers'}</p><div className="grid gap-4 md:grid-cols-2">{resource.data.results.map((person) => <article key={person.id} className="page-panel min-w-0 space-y-3"><h2 className="break-words text-lg font-bold">{person.name || person.username}</h2><p className="break-all text-sm">{person.email}</p><p className="text-sm text-muted-foreground">{staff ? person.username : `${person.country_code} ${person.phone}`}</p>{person.id === user?.id ? <p className="text-sm text-muted-foreground">Your account</p> : <ConfirmAction label={`Delete ${person.name || person.username}`} title="Delete this account?" description="The account and its cart, wishlist, messages, orders and payment records will be permanently deleted." action={async () => { await staffService.remove(staff ? 'accounts' : 'users', person.id); setPage(1); resource.reload() }} />}</article>)}</div>{!resource.data.count && <p className="page-panel">No accounts found.</p>}<nav aria-label="Account pages" className="flex justify-center gap-4"><Button variant="outline" disabled={!resource.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!resource.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav></>}</section>
}
