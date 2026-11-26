import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { SeverityBadge, StatusBadge } from '../../components/Badges'
import { ApiError } from '../../lib/api'
import { formatDate, formatRelative, formatShortDate } from '../../lib/format'
import { loadMyReports } from '../../lib/myReports'
import { track } from '../../lib/reports'
import type { TrackResult } from '../../lib/types'

/** P5 Track: enter a code, or pick one of this phone's reports; status page with timeline. */
export function TrackPage() {
  const { t } = useTranslation()
  const { code } = useParams()
  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t('track.title')}</h1>
      <CodeForm initial={code ?? ''} />
      {code ? <Status code={code} /> : <MyReports />}
    </section>
  )
}

function CodeForm({ initial }: { initial: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [value, setValue] = useState(initial)
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        const c = value.trim().toUpperCase()
        if (c) navigate(`/track/${c.startsWith('RS-') ? c : `RS-${c.replace(/^RS/, '')}`}`)
      }}
    >
      <div className="flex-1">
        <label htmlFor="code" className="label">
          {t('track.fieldLabel')}
        </label>
        <input
          id="code"
          className="input font-mono uppercase"
          placeholder={t('track.placeholder')}
          autoCapitalize="characters"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>
      <button type="submit" className="btn btn-primary self-end">
        {t('track.submit')}
      </button>
    </form>
  )
}

function MyReports() {
  const { t } = useTranslation()
  const mine = loadMyReports()
  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold">{t('track.myReports')}</h2>
      {mine.length === 0 ? (
        <div className="card flex flex-col items-start gap-3">
          <p>{t('empty.myReports')}</p>
          <Link to="/report" className="btn btn-primary">
            {t('buttons.reportPothole')}
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {mine.map((r) => (
            <li key={r.code}>
              <Link to={`/track/${r.code}`} className="card flex items-center gap-3 hover:border-brand-600">
                {r.thumbUrl ? (
                  <img src={r.thumbUrl} alt="" className="h-12 w-12 rounded-lg object-cover" />
                ) : (
                  <span className="h-12 w-12 rounded-lg bg-slate-100" />
                )}
                <span className="font-mono text-lg font-semibold">{r.code}</span>
                <span className="ml-auto text-sm text-slate-600">{formatRelative(r.createdAt)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Status({ code }: { code: string }) {
  const { t } = useTranslation()
  const q = useQuery({
    queryKey: ['track', code],
    queryFn: () => track(code),
    refetchInterval: 30_000, // Backend Schema: tracking pages poll every 30 s
  })
  if (q.isLoading) return <p>{t('app.loading')}</p>
  if (q.error) {
    const notFound = q.error instanceof ApiError && q.error.code === 'not_found'
    return <Alert tone="error">{t(notFound ? 'errors.wrongCode' : 'errors.loadFailed')}</Alert>
  }
  return q.data ? <StatusCard data={q.data} /> : null
}

// eslint-disable-next-line react-refresh/only-export-components
export function citizenStatusLine(t: TFunction, d: TrackResult): string {
  if (!d.defect_status) return t('track.noDamage')
  const fixedAt = d.timeline.find((s) => s.status === 'fixed')?.at
  return t(`status.citizen.${d.defect_status}`, {
    date: formatShortDate(d.defect_status === 'fixed' && fixedAt ? fixedAt : d.created_at),
  })
}

function StatusCard({ data }: { data: TrackResult }) {
  const { t } = useTranslation()
  return (
    <article className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xl font-bold">{data.tracking_code}</span>
        {data.defect_status && <StatusBadge status={data.defect_status} />}
      </div>
      {data.image_url && (
        <img src={data.image_url} alt={t('track.photoAlt')} className="max-h-64 w-full rounded-xl object-cover" />
      )}
      <div className="flex flex-wrap items-center gap-2">
        {data.damage_class && <span className="font-semibold">{t(`damage.${data.damage_class}`)}</span>}
        {data.severity_label && <SeverityBadge label={data.severity_label} />}
      </div>
      <p aria-live="polite">{citizenStatusLine(t, data)}</p>
      {data.report_count && data.report_count > 1 && (
        <p className="text-slate-700">{t('track.reportCount', { count: data.report_count })}</p>
      )}
      {data.timeline.length > 0 && (
        <ol className="flex flex-col gap-0">
          {data.timeline.map((step, i) => (
            <li key={step.status} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={clsx(
                    'mt-1 h-4 w-4 rounded-full border-2',
                    step.at ? 'border-brand-700 bg-brand-700' : 'border-slate-300 bg-white',
                  )}
                  aria-hidden="true"
                />
                {i < data.timeline.length - 1 && <span className="w-0.5 flex-1 bg-slate-200" aria-hidden="true" />}
              </div>
              <div className="pb-4">
                <p className={clsx('font-medium', !step.at && 'text-slate-500')}>{t(`status.${step.status}`)}</p>
                {step.at && <p className="text-sm text-slate-600">{formatDate(step.at)}</p>}
              </div>
            </li>
          ))}
        </ol>
      )}
      {data.fixed_photo_url && (
        <figure>
          <figcaption className="mb-1 font-semibold">{t('track.fixedPhoto')}</figcaption>
          <img src={data.fixed_photo_url} alt={t('track.fixedPhotoAlt')} className="w-full rounded-xl" />
        </figure>
      )}
    </article>
  )
}
