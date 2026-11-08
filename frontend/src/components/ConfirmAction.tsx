import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { FormNotice } from './FormField'
import { errorMessage } from '@/lib/api'

export function ConfirmAction({ label, title, description, action }: { label: string; title: string; description: string; action: () => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function confirm() {
    setBusy(true); setError('')
    try { await action(); setOpen(false) }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  return <AlertDialog open={open} onOpenChange={(value) => { if (!busy) { setOpen(value); setError('') } }}>
    <AlertDialogTrigger asChild><Button variant="outline" size="sm">{label}</Button></AlertDialogTrigger>
    <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>{title}</AlertDialogTitle><AlertDialogDescription>{description}</AlertDialogDescription></AlertDialogHeader><FormNotice error={error} /><AlertDialogFooter><AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel><Button variant="destructive" disabled={busy} onClick={confirm}>{busy ? 'Please wait…' : 'Confirm'}</Button></AlertDialogFooter></AlertDialogContent>
  </AlertDialog>
}
