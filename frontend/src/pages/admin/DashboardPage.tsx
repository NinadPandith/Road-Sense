import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { SeverityBadge } from '../../components/Badges'
import { DefectMap, type MapPoint } from '../../components/DefectMap'
import { allDefects, getStats, listDefects } from '../../lib/admin'
import { formatNumber } from '../../lib/format'

/** A2 Dashboard: KPI cards, severity map, top 10 to fix, needs-review banner. */
export default function DashboardPage() {
  const { t } = useTranslation()
  const stats = useQuery({ queryKey: ['stats'], queryFn: getStats })
  const top = useQuery({ queryKey: ['defects', 'top10'], queryFn: () => listDefects({}, 1, 10) })
  const all = useQuery({ queryKey: ['defects', 'map'], queryFn: () => allDefects({}) })

  if (stats.error || top.error) return <Alert tone="error">{t('errors.loadFailed')}</Alert>

  const s = stats.data
  const kpis = [
    { label: t('admin.kpi.open'), value: s?.open_defects },
    { label: t('admin.kpi.dangerousOpen'), value: s?.dangerous_open },
    { label: t('admin.kpi.newWeek'), value: s?.new_this_week },
    { label: t('admin.kpi.fixedWeek'), value: s?.fixed_this_week },
  ]
  const points: MapPoint[] = (all.data ?? []).map((d) => ({
    id: d.id,
    lat: d.lat,
    lon: d.lon,
    severity: d.severity_label,
    popup: (
      <div className="flex flex-col gap-1 text-sm">
        {d.thumb_url && <img src={d.thumb_url} alt="" className="h-20 w-32 rounded object-cover" />}
        <strong>{d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown')}</strong>
        <SeverityBadge label={d.severity_label} />
        <Link to={`/admin/defects/${d.id}`}>{t('admin.openDetails')}</Link>
      </div>
    ),
  }))

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t('admin.nav.dashboard')}</h1>
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
        <DefectMap points={points} className="h-[480px]" label={t('admin.nav.dashboard')} />
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
