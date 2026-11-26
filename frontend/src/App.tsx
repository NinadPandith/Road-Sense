import { lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { Route, Routes } from 'react-router-dom'
import { AdminLayout } from './components/AdminLayout'
import { CitizenLayout } from './components/CitizenLayout'
import { Placeholder } from './components/Placeholder'
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
          <Route path="drive" element={<Placeholder title={t('drive.title')} message={t('drive.comingSoon')} />} />
          <Route path="map" element={<PublicMapPage />} />
          <Route path="results" element={<Placeholder title={t('results.title')} message={`${t('results.intro')} ${t('results.pending')}`} />} />
        </Route>
        <Route path="admin/login" element={<LoginPage />} />
        <Route path="admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="repairs" element={<RepairsPage />} />
          <Route path="defects/:id" element={<DefectDetailPage />} />
          <Route path="surveys" element={<Placeholder title={t('admin.nav.surveys')} />} />
          <Route path="analytics" element={<Placeholder title={t('admin.nav.analytics')} />} />
          <Route path="settings" element={<Placeholder title={t('admin.nav.settings')} />} />
        </Route>
        <Route path="*" element={<CitizenLayout />}>
          <Route path="*" element={<Placeholder title={t('errors.wrongCode')} message={t('errors.loadFailed')} />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
