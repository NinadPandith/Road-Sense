import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { HomeIcon, MapIcon, SearchIcon } from './Icons'

/** Public screens: a header and a bottom tab bar on phones (Home, Track, Map). */
export function CitizenLayout() {
  const { t } = useTranslation()
  const tabs = [
    { to: '/', label: t('nav.home'), icon: HomeIcon, end: true },
    { to: '/track', label: t('nav.track'), icon: SearchIcon, end: false },
    { to: '/map', label: t('nav.map'), icon: MapIcon, end: false },
  ]
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-3">
        {t('app.skipToContent')}
      </a>
      <header className="sticky top-0 z-[1000] border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-xl items-center px-4">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold text-brand-800">
            <img src="/icon.svg" alt="" className="h-8 w-8" />
            {t('app.name')}
          </Link>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-4 pt-4 pb-24">
        <Outlet />
      </main>
      <nav
        aria-label={t('nav.mainMenu')}
        className="fixed inset-x-0 bottom-0 z-[1000] border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]"
      >
        <ul className="mx-auto flex max-w-xl">
          {tabs.map(({ to, label, icon: Icon, end }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  clsx(
                    'flex min-h-14 flex-col items-center justify-center gap-0.5 text-sm',
                    isActive ? 'font-semibold text-brand-700' : 'text-slate-600',
                  )
                }
              >
                <Icon className="h-6 w-6" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
