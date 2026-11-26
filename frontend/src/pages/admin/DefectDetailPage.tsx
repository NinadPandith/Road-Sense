import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Circle, CircleMarker } from 'react-leaflet'
import { useParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { SeverityBadge, StatusBadge } from '../../components/Badges'
import { DefectMap } from '../../components/DefectMap'
import { FactorBars } from '../../components/FactorBars'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { changeStatus, getDefect, NEXT_ACTIONS } from '../../lib/admin'
import { useAuth } from '../../lib/auth'
import { formatDate, formatScore, formatTime } from '../../lib/format'
import type { DefectDetail, DefectStatus, DetectionOut } from '../../lib/types'

/** A4 Defect detail: photos with boxes, severity + priority breakdown, map, status, history. */
export default function DefectDetailPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const q = useQuery({ queryKey: ['defect', id], queryFn: () => getDefect(id) })
  if (q.isLoading) return <p>{t('app.loading')}</p>
  if (q.error)
    return (
      <Alert tone="error">
        {q.error instanceof ApiError && q.error.code === 'not_found' ? t('admin.detail.notFound') : t('errors.loadFailed')}
      </Alert>
    )
  const d = q.data!
  const top = d.reports.flatMap((r) => r.detections).sort((a, b) => b.severity_score - a.severity_score)[0]

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">
          {d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown')}
          {d.road_name && <span className="font-normal text-slate-600"> · {d.road_name}</span>}
        </h1>
        <StatusBadge status={d.status} />
        {d.rank && <span className="rounded-full bg-slate-900 px-3 py-1 text-sm font-bold text-white">{t('admin.detail.rankOf', { rank: d.rank })}</span>}
      </header>
      <p className="text-slate-700">{d.priority_reason}</p>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold">{t('admin.detail.photos')}</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {d.reports.map((r) => (
              <li key={r.id}>
                {r.image_url ? (
                  <PhotoWithBoxes url={r.image_url} detections={r.detections} alt={t('result.photoAlt', { severity: d.severity_label ? t(`severity.${d.severity_label}`) : '' })} />
                ) : (
                  <div className="h-32 rounded-lg bg-slate-100" />
                )}
                <p className="mt-1 text-sm text-slate-600">
                  {t('admin.detail.reportFrom', { source: t(`admin.detail.source.${r.source}`), code: r.tracking_code })} · {formatDate(r.created_at)}
                </p>
                {r.note && <p className="text-sm">“{r.note}”</p>}
              </li>
            ))}
          </ul>
        </section>

        <div className="flex flex-col gap-5">
          <section className="card">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">{t('admin.detail.whySeverity')}</h2>
              <span className="text-sm text-slate-600">{t('severity.aiSuggestion')}</span>
            </div>
            <div className="mb-3"><SeverityBadge label={d.severity_label} score={d.severity_score} /></div>
            {top ? (
              <FactorBars
                showNumbers
                factors={{ size: top.size_score, depth: top.depth_score, type: top.type_score, position: top.position_score }}
              />
            ) : (
              <p className="text-slate-600">{t('severity.unscored')}</p>
            )}
          </section>
          <PriorityCard d={d} />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold">{t('admin.detail.reportsOnMap')}</h2>
          <DefectMap
            className="h-72"
            label={t('admin.detail.reportsOnMap')}
            points={[{ id: d.id, lat: d.lat, lon: d.lon, severity: d.severity_label }]}
          >
            <Circle center={[d.lat, d.lon]} radius={d.merge_radius_m} pathOptions={{ color: '#0f766e', dashArray: '4' }} />
            {d.reports.map((r) => (
              <CircleMarker key={r.id} center={[r.lat, r.lon]} radius={3} pathOptions={{ color: '#334155' }} />
            ))}
          </DefectMap>
          <p className="mt-2 text-sm text-slate-600">
            {t('admin.detail.mergeCircle', { radius: d.merge_radius_m })} · {t('admin.detail.coordinates')}: {d.lat.toFixed(6)}, {d.lon.toFixed(6)}
          </p>
        </section>
        <div className="flex flex-col gap-5">
          <StatusControl d={d} />
          <History d={d} />
        </div>
      </div>
    </div>
  )
}

function PhotoWithBoxes({ url, detections, alt }: { url: string; detections: DetectionOut[]; alt: string }) {
  const { t } = useTranslation()
  const colour = { minor: '#15803d', moderate: '#d97706', dangerous: '#b91c1c' }
  return (
    <div className="relative">
      <img src={url} alt={alt} className="w-full rounded-lg" />
      {detections.map((det, i) => {
        const [x1, y1, x2, y2] = det.box
        return (
          <div
            key={i}
            className="absolute border-2"
            style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%`, width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%`, borderColor: colour[det.severity_label] }}
          >
            <span className="absolute -top-5 left-0 rounded px-1 text-xs text-white" style={{ background: colour[det.severity_label] }}>
              {t(`damage.${det.damage_class}`)} {Math.round(det.confidence * 100)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}

function PriorityCard({ d }: { d: DefectDetail }) {
  const { t } = useTranslation()
  const terms = d.priority_terms
  const rows: [string, string][] = [
    ['S', formatScore(terms.S)],
    ['R', formatScore(terms.R)],
    ['n', String(terms.n ?? '–')],
    ['t', String(terms.t ?? '–')],
    ['B', terms.B !== undefined ? terms.B.toFixed(1) : '–'],
  ]
  return (
    <section className="card">
      <h2 className="mb-3 text-lg font-semibold">{t('admin.detail.whyPriority')}</h2>
      <p className="mb-3 font-mono text-xs text-slate-600">{t('admin.detail.formula')}</p>
      <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt>{t(`admin.detail.term.${k}`)}</dt>
            <dd className="text-right tabular-nums">{v}</dd>
          </div>
        ))}
        <dt className="border-t border-slate-200 pt-1.5 font-semibold">{t('admin.priority')}</dt>
        <dd className="border-t border-slate-200 pt-1.5 text-right font-semibold tabular-nums">{d.priority.toFixed(2)}</dd>
      </dl>
      {d.sensitive_place && <p className="mt-3 text-sm text-slate-600">{t('admin.detail.nearPlace', { place: d.sensitive_place })}</p>}
      {d.reopened_count > 0 && <p className="mt-1 text-sm text-slate-600">{t('admin.detail.reopened', { count: d.reopened_count })}</p>}
    </section>
  )
}

function StatusControl({ d }: { d: DefectDetail }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { isEngineer } = useAuth()
  const actions = NEXT_ACTIONS[d.status]
  const [to, setTo] = useState<DefectStatus | ''>(actions[0] ?? '')
  const [reason, setReason] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const m = useMutation({
    mutationFn: () => changeStatus(d.id, to as DefectStatus, reason, photo),
    onSuccess: (updated) => {
      qc.setQueryData(['defect', d.id], updated)
      void qc.invalidateQueries({ queryKey: ['defects'] })
      void qc.invalidateQueries({ queryKey: ['stats'] })
      setReason('')
      setPhoto(null)
      setTo(NEXT_ACTIONS[updated.status][0] ?? '')
    },
  })
  return (
    <section className="card">
      <h2 className="mb-3 text-lg font-semibold">{t('admin.detail.status')}</h2>
      {!isEngineer ? (
        <p className="text-slate-600">{t('errors.demoReadOnly')}</p>
      ) : actions.length === 0 ? (
        <StatusBadge status={d.status} />
      ) : (
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            m.mutate()
          }}
        >
          <fieldset className="flex flex-wrap gap-2">
            <legend className="label">{t('admin.detail.changeTo')}</legend>
            {actions.map((a) => (
              <label key={a} className={`btn ${to === a ? 'btn-primary' : 'btn-secondary'} cursor-pointer`}>
                <input type="radio" name="to" value={a} checked={to === a} onChange={() => setTo(a)} className="sr-only" />
                {t(`status.action.${a}`)}
              </label>
            ))}
          </fieldset>
          <div>
            <label htmlFor="reason" className="label">{t('admin.detail.reason')}</label>
            <input id="reason" className="input" maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          {to === 'fixed' && (
            <div>
              <label htmlFor="fixed-photo" className="label">{t('admin.detail.fixedPhoto')}</label>
              <input id="fixed-photo" type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
            </div>
          )}
          {m.error && (
            <Alert tone="error">{t(m.error instanceof ApiError ? ERROR_KEYS[m.error.code] : 'errors.generic')}</Alert>
          )}
          <button type="submit" className="btn btn-primary" disabled={!to || m.isPending}>
            {t('admin.detail.save')}
          </button>
        </form>
      )}
    </section>
  )
}

function History({ d }: { d: DefectDetail }) {
  const { t } = useTranslation()
  return (
    <section className="card">
      <h2 className="mb-3 text-lg font-semibold">{t('admin.detail.history')}</h2>
      {d.history.length === 0 ? (
        <p>{t('admin.detail.noHistory')}</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {d.history.map((h, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">
                {h.from_status ? `${t(`status.${h.from_status}`)} → ` : ''}
                {t(`status.${h.to_status}`)}
              </span>
              <span className="text-slate-600">
                {' '}· {h.changed_by ?? t('admin.detail.system')} · {formatDate(h.created_at)}, {formatTime(h.created_at)}
              </span>
              {h.reason && <p className="text-slate-700">{h.reason}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
