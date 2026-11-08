import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ResourceState } from '@/components/ResourceState'
import { useResource } from '@/lib/use-resource'
import { money } from '@/lib/format'
import { staffService } from '@/features/staff/staff-service'
import { useAuth } from './auth-context'

export function StaffPage() {
  const { user } = useAuth()
  const resource = useResource('dashboard', useCallback((signal) => staffService.dashboard(signal), []))
  const dashboard = resource.data
  const metrics = dashboard ? [ ['Outstanding order value', money(dashboard.pending_total)], ['Completed order value', money(dashboard.completed_total)], ['Orders', dashboard.order_count], ['Products', dashboard.product_count], ['Customers', dashboard.customer_count], ['Staff accounts', dashboard.admin_count], ['Messages', dashboard.message_count], ['Featured products', dashboard.featured_count] ] : []
  return <section className="space-y-7"><div><p className="eyebrow">SportHub staff</p><h1 className="page-title mt-3">Staff workspace</h1><p>Welcome, {user?.name || user?.username}. Your staff account is active.</p></div>
    <nav aria-label="Staff navigation" className="flex flex-wrap gap-3">{[['/admin/catalog', 'Manage catalog'], ['/admin/orders', 'Manage orders'], ['/admin/users', 'Customers'], ['/admin/accounts', 'Staff accounts'], ['/admin/messages', 'Contact messages'], ['/account', 'Manage your profile']].map(([to, label]) => <Button asChild variant="outline" key={to}><Link to={to}>{label}</Link></Button>)}</nav>
    <ResourceState {...resource} /><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{metrics.map(([label, value]) => <div key={label} className="page-panel"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-3 break-words text-2xl font-bold">{value}</p></div>)}</div>
  </section>
}
