import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { SeverityBadge, StatusBadge } from '../../components/Badges'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { bulkStatus, downloadCsv, listDefects, type Filters } from '../../lib/admin'
import { useAuth } from '../../lib/auth'
import { formatNumber } from '../../lib/format'
import type { DefectStatus, RoadClass, SeverityLabel } from '../../lib/types'

const PAGE_SIZE = 25
const ROADS: RoadClass[] = ['major', 'secondary', 'tertiary', 'residential', 'unknown']
const SEVERITIES: SeverityLabel[] = ['dangerous', 'moderate', 'minor']
const STATUSES: DefectStatus[] = ['needs_review', 'reported', 'verified', 'assigned', 'fixed', 'rejected']
const SORTS = ['priority', 'severity', 'age', '-age', 'reports']

function filtersFrom(sp: URLSearchParams): Filters {
  const status = sp.getAll('status') as DefectStatus[]
  return {
    status: status.length ? status : undefined,
    severity: sp.getAll('severity') as SeverityLabel[],
    road_class: sp.getAll('road_class') as RoadClass[],
    ward_id: sp.getAll('ward_id'),
    survey_id: sp.get('survey_id') ?? undefined,
    from: sp.get('from') ?? undefined,
    to: sp.get('to') ?? undefined,
    sort: sp.get('sort') ?? 'priority',
  }
}

/** A3 Repair list: ranked table, filters (kept in the URL), bulk status, CSV/PDF export. */
export default function RepairsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { isEngineer } = useAuth()
  const [sp, setSp] = useSearchParams()
  const filters = filtersFrom(sp)
  const page = Number(sp.get('page') ?? 1)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [notice, setNotice] = useState<string | null>(null)

  const q = useQuery({
    queryKey: ['defects', 'list', sp.toString()],
    queryFn: () => listDefects(filters, page, PAGE_SIZE),
    placeholderData: (prev) => prev,
  })
  const bulk = useMutation({
    mutationFn: (to: DefectStatus) => bulkStatus([...selected], to),
    onSuccess: (res) => {
      setSelected(new Set())
      setNotice(
        [t('admin.bulkDone', { count: res.updated }), res.skipped.length ? t('admin.bulkSkipped', { count: res.skipped.length }) : '']
          .filter(Boolean)
          .join(' · '),
      )
      void qc.invalidateQueries({ queryKey: ['defects'] })
      void qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(sp)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'page') next.delete('page')
    setSp(next)
  }

  async function exportPdf() {
    const { exportWorkOrderPdf } = await import('../../lib/pdf')
    await exportWorkOrderPdf(filters)
  }

  const items = q.data?.items ?? []
  const pages = Math.max(1, Math.ceil((q.data?.total ?? 0) / PAGE_SIZE))
  const allSelected = items.length > 0 && items.every((d) => selected.has(d.id))
  const bulkError = bulk.error instanceof ApiError ? t(ERROR_KEYS[bulk.error.code]) : bulk.error ? t('errors.generic') : null

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{t('admin.nav.repairs')}</h1>

      <fieldset className="card grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <legend className="sr-only">{t('admin.filters')}</legend>
        <Select label={t('admin.statusCol')} value={sp.get('status') ?? ''} onChange={(v) => setParam('status', v)}
          options={[['', t('admin.openStatuses')], ...STATUSES.map((s) => [s, t(`status.${s}`)] as [string, string])]} />
        <Select label={t('admin.severity')} value={sp.get('severity') ?? ''} onChange={(v) => setParam('severity', v)}
          options={[['', t('admin.allSeverities')], ...SEVERITIES.map((s) => [s, t(`severity.${s}`)] as [string, string])]} />
        <Select label={t('admin.roadCol')} value={sp.get('road_class') ?? ''} onChange={(v) => setParam('road_class', v)}
          options={[['', t('admin.allRoads')], ...ROADS.map((r) => [r, t(`road.${r}`)] as [string, string])]} />
        <div>
          <label className="label" htmlFor="from">{t('admin.dateFrom')}</label>
          <input id="from" type="date" className="input" value={sp.get('from') ?? ''} onChange={(e) => setParam('from', e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="to">{t('admin.dateTo')}</label>
          <input id="to" type="date" className="input" value={sp.get('to') ?? ''} onChange={(e) => setParam('to', e.target.value)} />
        </div>
        <Select label={t('admin.sortBy')} value={sp.get('sort') ?? 'priority'} onChange={(v) => setParam('sort', v)}
          options={SORTS.map((s) => [s, t(`admin.sort.${s}`)] as [string, string])} />
      </fieldset>

      <div className="flex flex-wrap gap-2">
        {isEngineer && (
          <>
            <button type="button" className="btn btn-secondary" disabled={!selected.size || bulk.isPending} onClick={() => bulk.mutate('assigned')}>
              {t('admin.markAssigned')}
            </button>
            <button type="button" className="btn btn-secondary" disabled={!selected.size || bulk.isPending} onClick={() => bulk.mutate('fixed')}>
              {t('admin.markFixed')}
            </button>
          </>
        )}
        <button type="button" className="btn btn-secondary" onClick={() => void downloadCsv(filters)}>
          {t('admin.exportCsv')}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void exportPdf()}>
          {t('admin.exportPdf')}
        </button>
      </div>
      {notice && <Alert tone="success">{notice}</Alert>}
      {bulkError && <Alert tone="error">{bulkError}</Alert>}
      {q.error && <Alert tone="error">{t('errors.loadFailed')}</Alert>}

      {q.data && items.length === 0 ? (
        <div className="card flex flex-col items-start gap-3">
          <p>{t('empty.repairs')}</p>
          <button type="button" className="btn btn-secondary" onClick={() => setSp(new URLSearchParams())}>
            {t('buttons.clearFilters')}
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                {isEngineer && (
                  <th className="p-3">
                    <input
                      type="checkbox"
                      className="h-5 w-5"
                      aria-label={t('admin.selectAll')}
                      checked={allSelected}
                      onChange={() => setSelected(allSelected ? new Set() : new Set(items.map((d) => d.id)))}
                    />
                  </th>
                )}
                <th className="p-3">{t('admin.rank')}</th>
                <th className="p-3">{t('admin.photo')}</th>
                <th className="p-3">{t('admin.type')}</th>
                <th className="p-3">{t('admin.severity')}</th>
                <th className="p-3">{t('admin.priority')}</th>
                <th className="p-3">{t('admin.roadCol')}</th>
                <th className="p-3">{t('admin.ward')}</th>
                <th className="p-3 text-right">{t('admin.reports')}</th>
                <th className="p-3 text-right">{t('admin.age')}</th>
                <th className="p-3">{t('admin.statusCol')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((d) => (
                <tr key={d.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/admin/defects/${d.id}`)}>
                  {isEngineer && (
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="h-5 w-5"
                        aria-label={t('admin.selectRow', { rank: d.rank ?? '–' })}
                        checked={selected.has(d.id)}
                        onChange={() => {
                          const next = new Set(selected)
                          if (next.has(d.id)) next.delete(d.id)
                          else next.add(d.id)
                          setSelected(next)
                        }}
                      />
                    </td>
                  )}
                  <td className="p-3 font-semibold tabular-nums">{d.rank ? `#${d.rank}` : '–'}</td>
                  <td className="p-3">
                    {d.thumb_url ? <img src={d.thumb_url} alt="" className="h-10 w-14 rounded object-cover" /> : null}
                  </td>
                  <td className="p-3">
                    <Link to={`/admin/defects/${d.id}`} className="font-medium underline-offset-2 hover:underline" onClick={(e) => e.stopPropagation()}>
                      {d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown')}
                    </Link>
                  </td>
                  <td className="p-3"><SeverityBadge label={d.severity_label} /></td>
                  <td className="max-w-64 p-3 text-slate-700">{d.priority_reason}</td>
                  <td className="p-3">{d.road_name ?? t(`road.${d.road_class}`)}</td>
                  <td className="p-3">{d.ward?.name ?? '–'}</td>
                  <td className="p-3 text-right tabular-nums">{formatNumber(d.report_count)}</td>
                  <td className="p-3 text-right tabular-nums">{d.age_days}</td>
                  <td className="p-3"><StatusBadge status={d.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <nav className="flex items-center gap-3" aria-label={t('admin.pageOf', { page, pages })}>
          <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => setParam('page', String(page - 1))}>
            {t('admin.previous')}
          </button>
          <span>{t('admin.pageOf', { page, pages })}</span>
          <button type="button" className="btn btn-secondary" disabled={page >= pages} onClick={() => setParam('page', String(page + 1))}>
            {t('admin.next')}
          </button>
        </nav>
      )}
    </div>
  )
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: [string, string][]
}) {
  const id = `f-${label.replace(/\W+/g, '-').toLowerCase()}`
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </div>
  )
}
