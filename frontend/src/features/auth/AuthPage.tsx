import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice } from '@/components/FormField'
import { errorMessage } from '@/lib/api'
import { useAuth } from './auth-context'
import type { Registration } from './auth-service'

export function AuthPage({ mode }: { mode: 'login' | 'register' | 'staff' }) {
  const { user, login, register } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const isRegister = mode === 'register'
  const isStaff = mode === 'staff'
  const state = location.state as { from?: unknown } | null
  const from = state?.from
  const destination = typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') && !from.includes('\\') && !['/login', '/register', '/admin/login'].includes(from)
    ? from : isStaff ? '/admin' : '/account'

  if (user && (!isStaff || user.is_staff)) return <Navigate to={destination} replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) || '')
    setError('')
    setBusy(true)
    try {
      if (isRegister) {
        await register({ name: value('name'), email: value('email'), phone: value('phone'), country_code: value('country_code') as Registration['country_code'], password: value('password'), password_confirm: value('password_confirm') })
      } else {
        await login(isStaff ? { username: value('username'), password: value('password') } : { email: value('email'), password: value('password') })
      }
      navigate(destination, { replace: true })
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  return <section className="mx-auto grid max-w-5xl overflow-hidden rounded-2xl border bg-card shadow-sm md:grid-cols-2">
    <div className="flex flex-col justify-between bg-foreground p-8 text-background md:p-12">
      <div><p className="mb-6 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">For the love of sport</p><h1 className="text-4xl font-bold leading-tight">{isStaff ? 'Your team.\nYour workspace.' : 'Your next game\nstarts here.'}</h1><p className="mt-5 max-w-sm text-sm leading-7 text-background/75">{isStaff ? 'Sign in with your staff account to access SportHub administration.' : 'Welcome to SportHub. A place for your sporting life, on and off the field.'}</p></div>
      <p className="mt-10 flex items-center gap-2 text-sm text-background/75"><ShieldCheck className="size-5" aria-hidden="true" /> Your account, securely connected.</p>
    </div>
    <div className="p-7 sm:p-10">
      <h2 className="text-2xl font-semibold">{isRegister ? 'Create an account' : isStaff ? 'Staff sign in' : 'Welcome back'}</h2>
      <p className="mb-7 mt-2 text-sm text-muted-foreground">{isRegister ? 'Let’s get you ready for the next game.' : 'Enter your details to continue.'}</p>
      <form onSubmit={submit} className="space-y-5" aria-busy={busy}>
        <FormNotice error={error} />
        <fieldset disabled={busy} className="space-y-5">
          {isRegister && <FormField label="Full name" name="name" autoComplete="name" maxLength={100} required />}
          {isStaff ? <FormField label="Staff username" name="username" autoComplete="username" maxLength={150} required /> : <FormField label="Email address" name="email" type="email" autoComplete="email" maxLength={254} required />}
          {isRegister && <div className="grid grid-cols-[110px_1fr] gap-3">
            <label className="space-y-2 text-sm font-medium"><span className="block">Country code</span><select name="country_code" defaultValue="+977" className="h-9 w-full rounded-md border border-input bg-background px-2" autoComplete="tel-country-code"><option value="+977">NP +977</option><option value="+91">IN +91</option></select></label>
            <FormField label="Phone number" name="phone" type="tel" autoComplete="tel-national" inputMode="numeric" pattern="[0-9]{10}" maxLength={10} title="Enter a 10-digit phone number" required />
          </div>}
          <FormField label="Password" name="password" type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={isRegister ? 8 : undefined} maxLength={128} required help={isRegister ? 'Use at least 8 characters and a special character. Avoid common passwords or personal details.' : undefined} />
          {isRegister && <FormField label="Confirm password" name="password_confirm" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />}
          <Button type="submit" className="w-full" size="lg">{busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}<ArrowRight aria-hidden="true" /></Button>
        </fieldset>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">{isRegister ? 'Already have an account? ' : isStaff ? 'Shopping with us? ' : 'New to SportHub? '}<Link className="font-semibold text-primary hover:underline" to={isRegister || isStaff ? '/login' : '/register'}>{isRegister || isStaff ? 'Customer sign in' : 'Create an account'}</Link></p>
    </div>
  </section>
}
