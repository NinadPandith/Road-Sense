import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { SeverityBadge } from '../../components/Badges'
import { DefectMap, type MapPoint } from '../../components/DefectMap'
import { SeverityIcon } from '../../components/Icons'
import { formatDate } from '../../lib/format'
import { supabase } from '../../lib/supabase'
import type { DamageClass, DefectStatus, SeverityLabel } from '../../lib/types'

const LEGEND_CLASS = { minor: 'text-minor', moderate: 'text-moderate', dangerous: 'text-dangerous' } as const

interface PublicDefect {
  id: string
  lat: number
  lon: number
  damage_class: DamageClass | null
  severity_label: SeverityLabel | null
  status: DefectStatus
  report_count: number
  first_reported_at: string
  fixed_at: string | null
}

/** P7 Public map: open defects + fixed in the last 30 days, from the public_defects view. */
export default function PublicMapPage() {
  const { t } = useTranslation()
  const q = useQuery({
    queryKey: ['public_defects'],
    enabled: !!supabase,
    queryFn: async () => {
      const { data, error } = await supabase!
        .from('public_defects')
        .select('id, lat, lon, damage_class, severity_label, status, report_count, first_reported_at, fixed_at')
        .limit(2000)
      if (error) throw error
      return data as PublicDefect[]
    },
  })
  const rows = q.data ?? []
  const points: MapPoint[] = rows.map((d) => ({
    id: d.id,
    lat: d.lat,
    lon: d.lon,
    severity: d.severity_label,
    fixed: d.status === 'fixed',
    popup: (
      <div className="flex flex-col gap-1 text-sm">
        <strong>{d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown')}</strong>
        <SeverityBadge label={d.severity_label} />
        <span>{t(`status.${d.status}`)} · {formatDate(d.first_reported_at)}</span>
      </div>
    ),
  }))
  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{t('publicMap.title')}</h1>
      <ul className="flex flex-wrap gap-3 text-sm" aria-label={t('publicMap.legend')}>
        {(['minor', 'moderate', 'dangerous'] as const).map((s) => (
          <li key={s} className="flex items-center gap-1">
            <SeverityIcon label={s} className={`h-3.5 w-3.5 ${LEGEND_CLASS[s]}`} />
            {t(`severity.${s}`)}
          </li>
        ))}
        <li className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-full bg-blue-600" aria-hidden="true" />
          {t('publicMap.fixedLegend')}
        </li>
      </ul>
      <DefectMap points={points} className="h-[60dvh]" label={t('publicMap.title')} />
      {!q.isLoading && rows.length === 0 && (
        <div className="card flex flex-col items-start gap-3">
          <p>{t('empty.map')}</p>
          <Link to="/report" className="btn btn-primary">
            {t('buttons.reportPothole')}
          </Link>
        </div>
      )}
    </section>
  )
}
