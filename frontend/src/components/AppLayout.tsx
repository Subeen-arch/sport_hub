import { useState } from 'react'
import { Dumbbell, LogOut, Menu, UserRound } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { useAuth } from '@/features/auth/auth-context'
import { errorMessage } from '@/lib/api'
import { FormNotice } from './FormField'
import { useCommerce } from '@/features/commerce/commerce-context'

export function AppLayout() {
  const { user, logout } = useAuth()
  const basket = useCommerce()
  const [menuOpen, setMenuOpen] = useState(false)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const links = [{ to: '/', label: 'Home' }, { to: '/shop', label: 'Shop' }, { to: '/search', label: 'Search' }, { to: '/about', label: 'About' }, { to: '/contact', label: 'Contact' }, ...(user ? [{ to: '/account', label: 'My account' }] : []) , ...(user?.is_staff ? [{ to: '/admin', label: 'Staff workspace' }] : [])]

  async function signOut() {
    setBusy(true)
    setError('')
    try { await logout(); setLogoutOpen(false) }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  return <div className="flex min-h-screen flex-col">
    <a href="#main-content" className="sr-only z-50 bg-background p-3 focus:not-sr-only focus:fixed">Skip to content</a>
    <div className="bg-foreground px-4 py-2 text-center text-xs tracking-wide text-background">Made for the love of sport.</div>
    <header className="border-b bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link to="/" className="flex items-center gap-2 text-2xl font-extrabold tracking-tight"><Dumbbell className="size-7 text-primary" aria-hidden="true" />SportHub<span className="text-primary">.</span></Link>
        <nav aria-label="Main navigation" className="hidden items-center gap-7 xl:flex">{links.map((link) => <NavLink end key={link.to} to={link.to} className={({ isActive }) => `text-sm font-medium ${isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}>{link.label}</NavLink>)}</nav>
        <div className="flex items-center gap-2">
          {user ? <>
            <Button asChild variant="ghost" className="hidden sm:inline-flex"><Link to="/account"><UserRound aria-hidden="true" /><span className="max-w-32 truncate">{user.name || user.username}</span></Link></Button>
            <AlertDialog open={logoutOpen} onOpenChange={(open) => { if (!busy) { setLogoutOpen(open); setError('') } }}>
              <AlertDialogTrigger asChild><Button variant="outline" size="sm"><LogOut aria-hidden="true" />Sign out</Button></AlertDialogTrigger>
              <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Sign out of SportHub?</AlertDialogTitle><AlertDialogDescription>You can sign back in whenever you’re ready.</AlertDialogDescription></AlertDialogHeader><FormNotice error={error} /><AlertDialogFooter><AlertDialogCancel disabled={busy}>Stay signed in</AlertDialogCancel><Button disabled={busy} onClick={signOut}>{busy ? 'Signing out…' : 'Sign out'}</Button></AlertDialogFooter></AlertDialogContent>
            </AlertDialog>
          </> : <Button asChild size="sm"><Link to="/login">Sign in</Link></Button>}
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}><SheetTrigger asChild><Button variant="ghost" size="icon" className="xl:hidden" aria-label="Open navigation"><Menu /></Button></SheetTrigger><SheetContent><SheetTitle className="px-6 pt-6">SportHub navigation</SheetTitle><SheetDescription className="sr-only">Navigate to your SportHub pages.</SheetDescription><nav className="grid gap-1 p-6" aria-label="Mobile navigation">{links.map((link) => <NavLink key={link.to} to={link.to} onClick={() => setMenuOpen(false)} className="rounded-md p-3 hover:bg-muted">{link.label}</NavLink>)}</nav></SheetContent></Sheet>
        </div>
      </div>
      <nav aria-label="Shopping navigation" className="mx-auto flex max-w-7xl flex-wrap justify-end gap-6 border-t px-5 py-3 text-sm sm:px-8"><Link to="/wishlist" className="hover:text-primary">Wishlist{user && basket.data ? ` (${basket.data.wishlist.count})` : ''}</Link><Link to="/cart" className="hover:text-primary">Cart{user && basket.data ? ` (${basket.data.cart.count})` : ''}</Link>{user && <><Link to="/orders" className="hover:text-primary">Your orders</Link><Link to="/payments" className="hover:text-primary">Your payments</Link></>}</nav>
    </header>
    <main id="main-content" className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 sm:py-14"><Outlet /></main>
    <footer className="border-t bg-card"><div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-4 px-5 py-6 text-sm text-muted-foreground sm:px-8"><p>SportHub · Find your game.</p><Link to={user?.is_staff ? '/admin' : '/admin/login'} className="hover:text-primary">Staff access</Link></div></footer>
  </div>
}
