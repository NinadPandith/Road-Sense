import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { LoginError, useAuth } from '../../lib/auth'
import { DEMO_EMAIL, DEMO_PASSWORD } from '../../lib/config'

/** A1 Login: email + password (Supabase Auth) and a read-only demo account. */
export default function LoginPage() {
  const { t } = useTranslation()
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/admin'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (session) return <Navigate to={from} replace />

  async function login(e: string, p: string) {
    setBusy(true)
    setError(null)
    try {
      await signIn(e, p)
      navigate(from, { replace: true })
    } catch (err) {
      const kind = err instanceof LoginError ? err.kind : 'wrong'
      setError(
        kind === 'locked' ? t('errors.locked') : kind === 'not_configured' ? t('errors.notConfigured') : t('errors.wrongPassword'),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-5 p-4">
      <div className="flex items-center gap-2 text-brand-800">
        <img src="/icon.svg" alt="" className="h-9 w-9" />
        <span className="text-xl font-bold">{t('app.name')}</span>
      </div>
      <h1 className="text-2xl font-bold">{t('admin.loginTitle')}</h1>
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          void login(email, password)
        }}
      >
        <div>
          <label htmlFor="email" className="label">{t('admin.email')}</label>
          <input id="email" type="email" autoComplete="username" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="label">{t('admin.password')}</label>
          <input id="password" type="password" autoComplete="current-password" required className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <Alert tone="error">{error}</Alert>}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {t('buttons.signIn')}
        </button>
      </form>
      <hr className="border-slate-200" />
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void login(DEMO_EMAIL, DEMO_PASSWORD)}>
        {t('admin.demo')}
      </button>
      <p className="text-sm text-slate-600">{t('admin.demoHint', { email: DEMO_EMAIL, password: DEMO_PASSWORD })}</p>
    </main>
  )
}
