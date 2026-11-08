import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ResourceState } from '@/components/ResourceState'
import { ConfirmAction } from '@/components/ConfirmAction'
import { useResource } from '@/lib/use-resource'
import { staffService } from './staff-service'

export function StaffMessagesPage() {
  const [page, setPage] = useState(1)
  const resource = useResource(String(page), useCallback((signal) => staffService.messages(page, signal), [page]))
  return <section className="space-y-6"><Link to="/admin" className="text-primary hover:underline">Staff workspace</Link><h1 className="page-title">Contact messages</h1><ResourceState {...resource} />{resource.data && <><p>{resource.data.count} messages</p><div className="grid gap-5 md:grid-cols-2">{resource.data.results.map((message) => <article key={message.id} className="page-panel min-w-0 space-y-3"><h2 className="break-words text-lg font-bold">{message.name}</h2><p className="text-xs text-muted-foreground">{new Date(message.created_at).toLocaleString('en-NP', { timeZone: 'Asia/Kathmandu' })}</p><p className="whitespace-pre-wrap break-words leading-7">{message.message}</p><p className="break-all text-sm">{message.email}</p><p className="text-sm">{message.country_code} {message.phone}</p><ConfirmAction label={`Delete message from ${message.name}`} title="Delete this message?" description="The contact message will be permanently removed." action={async () => { await staffService.remove('messages', message.id); setPage(1); resource.reload() }} /></article>)}</div>{!resource.data.count && <p className="page-panel">No contact messages yet.</p>}<nav aria-label="Message pages" className="flex justify-center gap-4"><Button variant="outline" disabled={!resource.data.previous} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button variant="outline" disabled={!resource.data.next} onClick={() => setPage(page + 1)}>Next</Button></nav></>}</section>
}
