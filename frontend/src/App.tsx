import { lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Route, Routes } from 'react-router-dom'
import { AdminLayout } from './components/AdminLayout'
import { CitizenLayout } from './components/CitizenLayout'
import { CapturePage } from './pages/citizen/CapturePage'
import { HomePage } from './pages/citizen/HomePage'
import { ResultPage } from './pages/citizen/ResultPage'
import { ReviewPage } from './pages/citizen/ReviewPage'
import { TrackPage } from './pages/citizen/TrackPage'

// Admin and map screens load on demand so the citizen report flow stays small on phones.
const LoginPage = lazy(() => import('./pages/admin/LoginPage'))
const DashboardPage = lazy(() => import('./pages/admin/DashboardPage'))
const RepairsPage = lazy(() => import('./pages/admin/RepairsPage'))
const DefectDetailPage = lazy(() => import('./pages/admin/DefectDetailPage'))
const PublicMapPage = lazy(() => import('./pages/citizen/PublicMapPage'))
const DrivePage = lazy(() => import('./pages/citizen/DrivePage'))
const ResultsPage = lazy(() => import('./pages/citizen/ResultsPage'))
const SurveysPage = lazy(() => import('./pages/admin/SurveysPage'))
const AnalyticsPage = lazy(() => import('./pages/admin/AnalyticsPage'))
const SettingsPage = lazy(() => import('./pages/admin/SettingsPage'))

/** 15 screens from docs/app-flow.md: P1–P8 public, A1–A7 engineer. */
export default function App() {
  const { t } = useTranslation()
  return (
    <Suspense fallback={<p className="p-6">{t('app.loading')}</p>}>
      <Routes>
        <Route element={<CitizenLayout />}>
          <Route index element={<HomePage />} />
          <Route path="report" element={<CapturePage />} />
          <Route path="report/review" element={<ReviewPage />} />
          <Route path="report/result/:code" element={<ResultPage />} />
          <Route path="track" element={<TrackPage />} />
          <Route path="track/:code" element={<TrackPage />} />
          <Route path="drive" element={<DrivePage />} />
          <Route path="map" element={<PublicMapPage />} />
          <Route path="results" element={<ResultsPage />} />
        </Route>
        <Route path="admin/login" element={<LoginPage />} />
        <Route path="admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="repairs" element={<RepairsPage />} />
          <Route path="defects/:id" element={<DefectDetailPage />} />
          <Route path="surveys" element={<SurveysPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<CitizenLayout />}>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

function NotFound() {
  const { t } = useTranslation()
  return (
    <section className="flex flex-col items-start gap-4">
      <h1 className="text-2xl font-bold">{t('app.notFound')}</h1>
      <Link to="/" className="btn btn-primary">
        {t('app.goHome')}
      </Link>
    </section>
  )
}
