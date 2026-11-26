import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { SeverityBadge } from '../../components/Badges'
import { CodeBox } from '../../components/CodeBox'
import { FactorBars } from '../../components/FactorBars'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { recallResult, sendAnyway, track } from '../../lib/reports'
import type { ReportResult } from '../../lib/types'

/** P4 Result: AI result card, merged or new, tracking code. */
export function ResultPage() {
  const { t } = useTranslation()
  const { code = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const initial = (location.state as { result?: ReportResult } | null)?.result ?? recallResult(code)
  const [result, setResult] = useState<ReportResult | null>(initial)

  // After a reload with no saved result, fall back to the tracking endpoint.
  const tracked = useQuery({ queryKey: ['track', code], queryFn: () => track(code), enabled: !result })
  const anyway = useMutation({ mutationFn: () => sendAnyway(code), onSuccess: setResult })

  if (!result) {
    if (tracked.isLoading) return <p>{t('app.loading')}</p>
    if (tracked.data) {
      navigate(`/track/${code}`, { replace: true })
      return null
    }
    return <Alert tone="error">{t('errors.wrongCode')}</Alert>
  }

  if (result.outcome === 'no_damage') {
    return (
      <section className="flex flex-col gap-5">
        <Alert tone="warning">{t('errors.noDamage')}</Alert>
        {result.image_url && <img src={result.image_url} alt={t('review.photoAlt')} className="max-h-64 w-full rounded-xl object-cover" />}
        {anyway.error && (
          <Alert tone="error">
            {t(anyway.error instanceof ApiError ? ERROR_KEYS[anyway.error.code] : 'errors.generic')}
          </Alert>
        )}
        <button type="button" className="btn btn-primary min-h-14" onClick={() => navigate('/report')}>
          {t('buttons.retakePhoto')}
        </button>
        <button type="button" className="btn btn-secondary" disabled={anyway.isPending} onClick={() => anyway.mutate()}>
          {t('buttons.sendAnyway')}
        </button>
      </section>
    )
  }

  const title =
    result.outcome === 'merged'
      ? t('result.titleMerged')
      : result.outcome === 'needs_review'
        ? t('result.titleNeedsReview')
        : result.outcome === 'processing'
          ? t('result.titleProcessing')
          : t('result.titleNew')
  const sev = result.severity
  const typeName = result.damage_class ? t(`damage.${result.damage_class}`) : null

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold" aria-live="polite">
        {title}
      </h1>
      {result.outcome === 'merged' && result.report_count && (
        <p className="text-lg">{t('result.mergedDetail', { count: result.report_count })}</p>
      )}

      {sev && typeName && (
        <article className="card flex flex-col gap-4">
          <div className="flex gap-4">
            {result.thumb_url && (
              <img
                src={result.thumb_url}
                alt={t('result.photoAlt', { severity: t(`severity.${sev.label}`) })}
                className="h-24 w-24 shrink-0 rounded-lg object-cover"
              />
            )}
            <div className="flex flex-col gap-2">
              <p className="text-slate-700">{t('result.aiFound', { type: typeName.toLowerCase() })}</p>
              <p className="text-lg font-semibold">
                {typeName}
                {result.confidence_label && <> · {t(`confidence.${result.confidence_label}`)}</>}
              </p>
              <SeverityBadge label={sev.label} size="lg" />
            </div>
          </div>
          <p>{t('result.because', { label: t(`severity.${sev.label}`), reason: sev.reason })}</p>
          <div>
            <h2 className="mb-2 font-semibold">{t('result.breakdown')}</h2>
            <FactorBars factors={sev.factors} />
          </div>
        </article>
      )}

      <CodeBox code={result.tracking_code} />

      <div className="flex flex-col gap-3">
        <Link to="/" className="btn btn-primary min-h-14">
          {t('result.done')}
        </Link>
        <Link to={`/track/${result.tracking_code}`} className="btn btn-secondary">
          {t('result.trackThis')}
        </Link>
      </div>
    </section>
  )
}
