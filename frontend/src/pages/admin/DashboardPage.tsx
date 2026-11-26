import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { DefectMap } from '../../components/DefectMap'
import { ClusterLayer, HeatLayer, type LayerPoint } from '../../components/MapLayers'
import { allDefects, getStats, listDefects, type Filters } from '../../lib/admin'
import { formatNumber } from '../../lib/format'

/** A2 Dashboard: KPI cards, clustered severity map with heatmap toggle, top 10, review banner.
 * `?survey_id=` filters the map and list to one survey (Surveys -> View on map). */
export default function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const surveyId = sp.get('survey_id') ?? undefined
  const filters: Filters = useMemo(() => ({ survey_id: surveyId }), [surveyId])
  const [heat, setHeat] = useState(false)

  const stats = useQuery({ queryKey: ['stats'], queryFn: () => getStats() })
  const top = useQuery({ queryKey: ['defects', 'top10', surveyId], queryFn: () => listDefects(filters, 1, 10) })
  const all = useQuery({ queryKey: ['defects', 'map', surveyId], queryFn: () => allDefects(filters) })

  const points: LayerPoint[] = useMemo(
    () =>
      (all.data ?? []).map((d) => ({
        id: d.id,
        lat: d.lat,
        lon: d.lon,
        severity: d.severity_label,
        title: d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown'),
        subtitle: d.severity_label ? t(`severity.${d.severity_label}`) : t('severity.unscored'),
        linkText: t('admin.openDetails'),
        href: `/admin/defects/${d.id}`,
      })),
    [all.data, t],
  )

  if (stats.error || top.error) return <Alert tone="error">{t('errors.loadFailed')}</Alert>

  const s = stats.data
  const kpis = [
    { label: t('admin.kpi.open'), value: s?.open_defects },
    { label: t('admin.kpi.dangerousOpen'), value: s?.dangerous_open },
    { label: t('admin.kpi.newWeek'), value: s?.new_this_week },
    { label: t('admin.kpi.fixedWeek'), value: s?.fixed_this_week },
  ]

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t('admin.nav.dashboard')}</h1>
      {surveyId && (
        <Alert tone="info" action={<Link to="/admin" className="btn btn-secondary">{t('admin.showAll')}</Link>}>
          {t('admin.surveyFilter')}
        </Alert>
      )}
      {s && s.needs_review > 0 && (
        <Alert
          tone="info"
          action={
            <Link to="/admin/repairs?status=needs_review" className="btn btn-secondary">
              {t('admin.openDetails')}
            </Link>
          }
        >
          {t('admin.needsReviewBanner', { count: s.needs_review })}
        </Alert>
      )}
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {kpis.map((k) => (
          <li key={k.label} className="card">
            <p className="text-sm text-slate-600">{k.label}</p>
            <p className="text-3xl font-bold tabular-nums">{k.value === undefined ? '–' : formatNumber(k.value)}</p>
          </li>
        ))}
      </ul>
      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 self-end text-sm font-medium">
            <input type="checkbox" className="h-5 w-5" checked={heat} onChange={(e) => setHeat(e.target.checked)} />
            {t('admin.heatmap')}
          </label>
          <DefectMap
            points={points.map((p) => ({ id: p.id, lat: p.lat, lon: p.lon, severity: p.severity }))}
            markers={false}
            className="h-[480px]"
            label={t('admin.nav.dashboard')}
          >
            {heat ? <HeatLayer points={points} /> : <ClusterLayer points={points} onOpen={navigate} />}
          </DefectMap>
          {all.data && all.data.length === 0 && <p className="text-slate-600">{t('empty.dashboard')}</p>}
        </div>
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold">{t('admin.fixFirst')}</h2>
          {top.data && top.data.items.length === 0 && <p>{t('empty.dashboard')}</p>}
          <ol className="flex flex-col divide-y divide-slate-100">
            {top.data?.items.map((d) => (
              <li key={d.id}>
                <Link to={`/admin/defects/${d.id}`} className="flex gap-3 py-2.5 hover:bg-slate-50">
                  <span className="w-8 shrink-0 text-lg font-bold tabular-nums text-slate-500">#{d.rank}</span>
                  <span className="flex flex-col">
                    <span className="font-medium">
                      {d.road_name ?? (d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown'))}
                    </span>
                    <span className="text-sm text-slate-600">{d.priority_reason}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  )
}
