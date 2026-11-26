import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Alert } from '../../components/Alert'
import { SEVERITY_COLOURS } from '../../components/Badges'
import { getStats } from '../../lib/admin'
import { formatShortDate } from '../../lib/format'
import type { SeverityLabel } from '../../lib/types'

// Categorical slots 1 and 2 of the validated reference palette (dataviz skill): blue, orange.
const SERIES = { reported: '#257de0', fixed: '#f47230' }
const SINGLE = '#257de0'
const GRID = '#e2e8f0'
const AXIS = '#475569'
const RANGES = [8, 12, 26]

/** A6 Analytics: open defects by severity, by ward, and reported vs fixed per week.
 * Every chart has a table view (relief for the low-contrast orange, and for screen readers). */
export default function AnalyticsPage() {
  const { t } = useTranslation()
  const [weeks, setWeeks] = useState(8)
  const q = useQuery({
    queryKey: ['stats', weeks],
    queryFn: () => getStats(new Date(Date.now() - weeks * 7 * 86400_000).toISOString()),
  })
  if (q.error) return <Alert tone="error">{t('errors.loadFailed')}</Alert>
  const s = q.data

  const severity = (['dangerous', 'moderate', 'minor'] as SeverityLabel[]).map((k) => ({
    key: k,
    label: t(`severity.${k}`),
    count: s?.open_by_severity.find((x) => x.key === k)?.count ?? 0,
  }))
  const wards = (s?.open_by_ward ?? []).slice(0, 12).map((w) => ({ label: w.key, count: w.count }))
  const perWeek = (s?.per_week ?? []).map((w) => ({
    label: formatShortDate(w.week_start),
    reported: w.reported,
    fixed: w.fixed,
  }))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('admin.nav.analytics')}</h1>
        <div>
          <label htmlFor="range" className="label">{t('analytics.range')}</label>
          <select id="range" className="input" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>
            {RANGES.map((w) => (
              <option key={w} value={w}>{t('analytics.lastWeeks', { count: w })}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title={t('analytics.bySeverity')} rows={severity.map((r) => [r.label, r.count])} cols={[t('admin.severity'), t('analytics.openDefects')]}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={severity} margin={{ top: 20, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 13 }} axisLine={{ stroke: GRID }} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: AXIS, fontSize: 12 }} axisLine={false} tickLine={false} width={36} />
              <Tooltip cursor={{ fill: '#f1f5f9' }} />
              <Bar dataKey="count" name={t('analytics.openDefects')} maxBarSize={24} radius={[4, 4, 0, 0]}>
                {severity.map((r) => (
                  <Cell key={r.key} fill={SEVERITY_COLOURS[r.key]} />
                ))}
                <LabelList dataKey="count" position="top" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title={t('analytics.byWard')} rows={wards.map((r) => [r.label, r.count])} cols={[t('admin.ward'), t('analytics.openDefects')]}>
          <ResponsiveContainer width="100%" height={Math.max(160, wards.length * 32 + 30)}>
            <BarChart data={wards} layout="vertical" margin={{ top: 0, right: 32, left: 8, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={{ fill: AXIS, fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" width={110} tick={{ fill: AXIS, fontSize: 13 }} axisLine={{ stroke: GRID }} tickLine={false} />
              <Tooltip cursor={{ fill: '#f1f5f9' }} />
              <Bar dataKey="count" name={t('analytics.openDefects')} fill={SINGLE} maxBarSize={24} radius={[0, 4, 4, 0]}>
                <LabelList dataKey="count" position="right" fill={AXIS} fontSize={12} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard
        title={t('analytics.perWeek')}
        rows={perWeek.map((r) => [r.label, r.reported, r.fixed])}
        cols={[t('analytics.weekOf'), t('analytics.reported'), t('analytics.fixed')]}
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={perWeek} margin={{ top: 12, right: 24, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 12 }} axisLine={{ stroke: GRID }} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: AXIS, fontSize: 12 }} axisLine={false} tickLine={false} width={36} />
            <Tooltip />
            <Legend wrapperStyle={{ color: AXIS, fontSize: 13 }} />
            <Line type="monotone" dataKey="reported" name={t('analytics.reported')} stroke={SERIES.reported} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: '#fff', fill: SERIES.reported }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="fixed" name={t('analytics.fixed')} stroke={SERIES.fixed} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: '#fff', fill: SERIES.fixed }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

function ChartCard({ title, children, rows, cols }: { title: string; children: React.ReactNode; rows: (string | number)[][]; cols: string[] }) {
  const { t } = useTranslation()
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div aria-hidden="true">{children}</div>
      <details>
        <summary className="cursor-pointer text-sm font-medium text-brand-800">{t('analytics.showTable')}</summary>
        <table className="mt-2 w-full text-left text-sm">
          <caption className="sr-only">{title}</caption>
          <thead>
            <tr>{cols.map((c) => <th key={c} className="py-1 pr-3 font-medium">{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-slate-100">
                {r.map((v, j) => <td key={j} className="py-1 pr-3 tabular-nums">{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  )
}
