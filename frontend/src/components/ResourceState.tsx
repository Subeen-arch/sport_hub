import { Button } from '@/components/ui/button'

export function ResourceState({ loading, error, reload }: { loading: boolean; error?: string; reload: () => void }) {
  if (loading) return <p role="status" className="py-8 text-muted-foreground">Loading…</p>
  if (error) return <div className="space-y-3 py-6"><p role="alert" className="text-destructive">{error}</p><Button variant="outline" onClick={reload}>Try again</Button></div>
  return null
}
