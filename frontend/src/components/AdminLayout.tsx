import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useRealtimeDefects } from '../lib/realtime'

/** Engineer screens: left sidebar for A2–A7; redirects to login and back when signed out. */
export function AdminLayout() {
  const { t } = useTranslation()
  const { ready, session, me, signOut } = useAuth()
  const location = useLocation()
  useRealtimeDefects(!!session)

  if (!ready) return <p className="p-6">{t('app.loading')}</p>
  if (!session) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname + location.search }} />
  }

  const links = [
    { to: '/admin', label: t('admin.nav.dashboard'), end: true },
    { to: '/admin/repairs', label: t('admin.nav.repairs') },
    { to: '/admin/surveys', label: t('admin.nav.surveys') },
    { to: '/admin/analytics', label: t('admin.nav.analytics') },
    { to: '/admin/settings', label: t('admin.nav.settings') },
  ]
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-3">
        {t('app.skipToContent')}
      </a>
      <aside className="border-b border-slate-200 bg-white md:w-56 md:border-r md:border-b-0">
        <div className="flex h-14 items-center gap-2 px-4">
          <Link to="/" className="flex items-center gap-2 font-bold text-brand-800">
            <img src="/icon.svg" alt="" className="h-7 w-7" />
            {t('app.name')}
          </Link>
        </div>
        <nav aria-label={t('nav.mainMenu')}>
          <ul className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:overflow-visible">
            {links.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end={l.end}
                  className={({ isActive }) =>
                    clsx(
                      'block min-h-11 rounded-lg px-3 py-2.5 whitespace-nowrap',
                      isActive ? 'bg-brand-50 font-semibold text-brand-800' : 'text-slate-700 hover:bg-slate-100',
                    )
                  }
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="hidden px-4 py-4 text-sm text-slate-600 md:block">
          <p className="font-medium text-slate-800">{me?.full_name}</p>
          <button type="button" className="mt-2 underline" onClick={() => void signOut()}>
            {t('admin.signOut')}
          </button>
        </div>
      </aside>
      <main id="main" className="min-w-0 flex-1 p-4 md:p-6">
        {me?.role === 'demo' && (
          <p className="mb-4 rounded-lg bg-violet-50 px-3 py-2 text-violet-900" role="status">
            {t('admin.demoBanner')}
          </p>
        )}
        <Outlet />
      </main>
    </div>
  )
}
