import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { listSurveys, uploadSurvey } from '../../lib/admin'
import { useAuth } from '../../lib/auth'
import { formatDate, formatTime } from '../../lib/format'
import type { Survey } from '../../lib/types'

const MAX_MB = 50
const ACTIVE: Survey['status'][] = ['queued', 'extracting', 'detecting', 'scoring', 'merging']

/** A5 Surveys: upload a ride video + GPX track, then watch the job. */
export default function SurveysPage() {
  const { t } = useTranslation()
  const { isEngineer } = useAuth()
  const [prefill, setPrefill] = useState('')
  const [warnings, setWarnings] = useState<Record<string, boolean>>({})
  const surveys = useQuery({
    queryKey: ['surveys'],
    queryFn: listSurveys,
    refetchInterval: (q) => (q.state.data?.some((s) => ACTIVE.includes(s.status)) ? 3000 : false),
  })

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t('admin.nav.surveys')}</h1>
      {isEngineer ? (
        <NewSurvey
          key={prefill}
          initialName={prefill}
          onUploaded={(s) => s.gpx_overlap === false && setWarnings((w) => ({ ...w, [s.id]: true }))}
        />
      ) : (
        <p className="text-slate-600">{t('errors.demoReadOnly')}</p>
      )}
      {surveys.error && <Alert tone="error">{t('errors.loadFailed')}</Alert>}
      <ul className="flex flex-col gap-3">
        {surveys.data?.map((s) => (
          <li key={s.id}>
            <SurveyCard s={s} gpxWarning={!!warnings[s.id]} onRetry={() => setPrefill(`${s.name} `)} canRetry={isEngineer} />
          </li>
        ))}
      </ul>
    </div>
  )
}

function NewSurvey({ initialName, onUploaded }: { initialName: string; onUploaded: (s: Survey) => void }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [name, setName] = useState(initialName.trim())
  const [video, setVideo] = useState<File | null>(null)
  const [gpx, setGpx] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [tooBig, setTooBig] = useState(false)
  const form = useRef<HTMLFormElement>(null)
  const upload = useMutation({
    mutationFn: () => uploadSurvey(name, video!, gpx!, setProgress),
    onSuccess: (s) => {
      onUploaded(s)
      setName('')
      setVideo(null)
      setGpx(null)
      setProgress(0)
      form.current?.reset()
      void qc.invalidateQueries({ queryKey: ['surveys'] })
    },
  })
  const error = upload.error instanceof ApiError ? upload.error : null
  return (
    <form
      ref={form}
      className="card flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        if (video && gpx && name.trim()) upload.mutate()
      }}
    >
      <h2 className="text-lg font-semibold">{t('surveys.new')}</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="sname" className="label">{t('surveys.name')}</label>
          <input id="sname" className="input" required maxLength={120} value={name} placeholder={t('surveys.namePlaceholder')} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label htmlFor="svideo" className="label">{t('surveys.video')}</label>
          <input
            id="svideo"
            type="file"
            accept="video/mp4"
            required
            className="block w-full text-sm"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null
              setTooBig(!!f && f.size > MAX_MB * 1024 * 1024)
              setVideo(f)
            }}
          />
        </div>
        <div>
          <label htmlFor="sgpx" className="label">{t('surveys.gpx')}</label>
          <input id="sgpx" type="file" accept=".gpx,application/gpx+xml" required className="block w-full text-sm" onChange={(e) => setGpx(e.target.files?.[0] ?? null)} />
        </div>
      </div>
      <p className="text-sm text-slate-600">{t('surveys.hint', { mb: MAX_MB })}</p>
      {tooBig && <Alert tone="error">{t('surveys.tooBig', { mb: MAX_MB })}</Alert>}
      {upload.isPending && (
        <div aria-live="polite">
          <p className="text-sm">{t('surveys.uploading', { percent: Math.round(progress * 100) })}</p>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        </div>
      )}
      {upload.error && (
        <Alert tone="error">{error?.code === 'survey_gpx_mismatch' || error?.code === 'invalid_image' ? error.message : t(error ? ERROR_KEYS[error.code] : 'errors.uploadFailed')}</Alert>
      )}
      <button type="submit" className="btn btn-primary self-start" disabled={upload.isPending || tooBig || !video || !gpx}>
        {t('surveys.upload')}
      </button>
    </form>
  )
}

const STEPS: Survey['status'][] = ['queued', 'extracting', 'detecting', 'scoring', 'merging', 'done']

function SurveyCard({ s, gpxWarning, onRetry, canRetry }: { s: Survey; gpxWarning: boolean; onRetry: () => void; canRetry: boolean }) {
  const { t } = useTranslation()
  const failed = s.status === 'failed'
  const done = s.status === 'done'
  const current = STEPS.indexOf(s.status)
  return (
    <article className={clsx('card flex flex-col gap-3', failed && 'border-red-300 bg-red-50')}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">{s.name}</h3>
        <span className="text-sm text-slate-600">
          {formatDate(s.created_at)}, {formatTime(s.created_at)}
        </span>
      </div>
      {gpxWarning && <Alert tone="warning">{t('surveys.gpxWarning')}</Alert>}
      {failed ? (
        <Alert
          tone="error"
          action={canRetry ? <button type="button" className="btn btn-secondary" onClick={onRetry}>{t('buttons.retry')}</button> : undefined}
        >
          {t('surveys.failed', { reason: s.error ?? t('errors.generic') })}
        </Alert>
      ) : done ? (
        <>
          <p className="text-lg">
            {t('surveys.doneCard', {
              found: s.detections_count,
              defects: s.defects_new + s.defects_merged,
              new: s.defects_new,
              merged: s.defects_merged,
            })}
          </p>
          <Link to={`/admin?survey_id=${s.id}`} className="btn btn-secondary self-start">
            {t('surveys.viewOnMap')}
          </Link>
        </>
      ) : (
        <div aria-live="polite">
          <ol className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {STEPS.slice(0, -1).map((step, i) => (
              <li key={step} className={clsx(i === current ? 'font-semibold text-brand-800' : i < current ? 'text-slate-700' : 'text-slate-400')}>
                {t(`surveys.state.${step}`)}
                {step === 'detecting' && i === current && ` ${s.progress}%`}
              </li>
            ))}
          </ol>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={s.progress} aria-valuemin={0} aria-valuemax={100} aria-label={t(`surveys.state.${s.status}`)}>
            <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${s.progress}%` }} />
          </div>
        </div>
      )}
    </article>
  )
}
