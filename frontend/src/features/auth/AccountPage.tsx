import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { FormField, FormNotice } from '@/components/FormField'
import { errorMessage } from '@/lib/api'
import { useAuth } from './auth-context'
import { authService, type ProfileChanges } from './auth-service'

export function AccountPage() {
  const { user, updateProfile } = useAuth()
  const [profileBusy, setProfileBusy] = useState(false)
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [profileNotice, setProfileNotice] = useState({ error: '', success: '' })
  const [passwordNotice, setPasswordNotice] = useState({ error: '', success: '' })
  if (!user) return null

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget)) as ProfileChanges
    setProfileBusy(true)
    setProfileNotice({ error: '', success: '' })
    try {
      await updateProfile(data)
      setProfileNotice({ error: '', success: 'Your profile has been updated.' })
    } catch (reason) {
      setProfileNotice({ error: errorMessage(reason), success: '' })
    } finally { setProfileBusy(false) }
  }

  async function savePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setPasswordBusy(true)
    setPasswordNotice({ error: '', success: '' })
    try {
      const result = await authService.changePassword({ old_password: String(data.get('old_password')), new_password: String(data.get('new_password')), password_confirm: String(data.get('password_confirm')) })
      form.reset()
      setPasswordNotice({ error: '', success: result.detail })
    } catch (reason) {
      setPasswordNotice({ error: errorMessage(reason), success: '' })
    } finally { setPasswordBusy(false) }
  }

  return <section className="mx-auto max-w-5xl">
    <p className="eyebrow">Your SportHub</p><h1 className="page-title">My account</h1><p className="mb-8 text-muted-foreground">Keep your details up to date and your account secure.</p>
    <div className="grid items-start gap-6 md:grid-cols-2">
      <form onSubmit={saveProfile} className="page-panel space-y-5" aria-busy={profileBusy}>
        <h2 className="text-xl font-semibold">Personal details</h2><FormNotice {...profileNotice} />
        <fieldset disabled={profileBusy || passwordBusy} className="space-y-5">
          <FormField label="Full name" name="name" defaultValue={user.name} autoComplete="name" maxLength={100} required />
          <FormField label="Email address" name="email" defaultValue={user.email} type="email" autoComplete="email" maxLength={254} required />
          {user.is_staff && <FormField label="Staff username" name="username" defaultValue={user.username} autoComplete="username" maxLength={150} required />}
          <label className="block space-y-2 text-sm font-medium"><span className="block">Country code</span><select className="h-9 w-full rounded-md border border-input bg-background px-3" name="country_code" defaultValue={user.country_code}><option value="+977">Nepal (+977)</option><option value="+91">India (+91)</option></select></label>
          <FormField label="Phone number" name="phone" defaultValue={user.phone} autoComplete="tel-national" type="tel" inputMode="numeric" pattern="[0-9]{10}" title="Enter a 10-digit phone number" maxLength={10} required />
          <Button type="submit">{profileBusy ? 'Saving…' : 'Save changes'}</Button>
        </fieldset>
      </form>
      <form onSubmit={savePassword} className="page-panel space-y-5" aria-busy={passwordBusy}>
        <h2 className="text-xl font-semibold">Change password</h2><FormNotice {...passwordNotice} />
        <fieldset disabled={passwordBusy || profileBusy} className="space-y-5">
          <FormField label="Current password" name="old_password" type="password" autoComplete="current-password" maxLength={128} required />
          <FormField label="New password" name="new_password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required help="Use at least 8 characters and a special character. Avoid common passwords or personal details." />
          <FormField label="Confirm new password" name="password_confirm" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
          <Button type="submit">{passwordBusy ? 'Updating…' : 'Update password'}</Button>
        </fieldset>
      </form>
    </div>
  </section>
}
