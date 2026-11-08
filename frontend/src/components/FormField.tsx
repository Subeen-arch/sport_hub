import { useId, type ComponentProps } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function FormField({ label, help, ...props }: ComponentProps<typeof Input> & { label: string; help?: string }) {
  const id = useId()
  return <div className="space-y-2">
    <Label htmlFor={id}>{label}</Label>
    <Input id={id} aria-describedby={help ? `${id}-help` : undefined} {...props} />
    {help && <p id={`${id}-help`} className="text-xs text-muted-foreground">{help}</p>}
  </div>
}

export function SelectField({ label, children, ...props }: ComponentProps<'select'> & { label: string }) {
  const id = useId()
  return <div className="filter-label"><Label htmlFor={id}>{label}</Label><select id={id} {...props}>{children}</select></div>
}

export function FormNotice({ error, success }: { error?: string; success?: string }) {
  if (error) return <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>
  if (success) return <p role="status" className="rounded-md border border-primary/30 bg-primary/5 p-3 text-sm text-primary">{success}</p>
  return null
}
