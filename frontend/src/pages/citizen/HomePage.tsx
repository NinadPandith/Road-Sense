import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { CameraIcon, CarIcon, SearchIcon } from '../../components/Icons'

export function HomePage() {
  const { t } = useTranslation()
  return (
    <section className="flex flex-col gap-6 pt-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('home.headline')}</h1>
        <p className="mt-2 text-lg text-slate-700">{t('home.subtext')}</p>
      </div>
      <div className="flex flex-col gap-3">
        <Link to="/report" className="btn btn-primary min-h-16 text-lg">
          <CameraIcon />
          {t('home.report')}
        </Link>
        <Link to="/track" className="btn btn-secondary min-h-14">
          <SearchIcon />
          {t('home.track')}
        </Link>
        <Link to="/drive" className="btn btn-secondary min-h-14">
          <CarIcon />
          {t('home.drive')}
        </Link>
      </div>
      <div className="flex flex-col gap-2 text-brand-800">
        <Link to="/map" className="underline underline-offset-4">
          {t('home.mapLink')}
        </Link>
        <Link to="/results" className="underline underline-offset-4">
          {t('home.resultsLink')}
        </Link>
        <Link to="/admin" className="text-sm text-slate-600 underline underline-offset-4">
          {t('home.engineerLink')}
        </Link>
      </div>
    </section>
  )
}
