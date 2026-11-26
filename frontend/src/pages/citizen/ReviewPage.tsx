import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { PinMap } from '../../components/PinMap'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { MAP_CENTER, PILOT_AREA_NAME, WEAK_GPS_M } from '../../lib/config'
import { useDraft } from '../../lib/draft'
import { enqueue, newId } from '../../lib/outbox'
import { submitReport } from '../../lib/reports'

/** P3 Review: photo, pin on a map, optional note, submit. Uploading progress is shown here. */
export function ReviewPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { draft, setDraft } = useDraft()
  const [pos, setPos] = useState<[number, number]>(
    draft?.fix ? [draft.fix.lat, draft.fix.lon] : MAP_CENTER,
  )
  const [moved, setMoved] = useState(false)
  const [note, setNote] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'slow'>('idle')
  const [error, setError] = useState<ApiError | null>(null)
  const [savedOffline, setSavedOffline] = useState(false)
  const onMove = useCallback((lat: number, lon: number) => {
    setPos([lat, lon])
    setMoved(true)
  }, [])

  useEffect(() => {
    if (state !== 'sending') return
    const id = window.setTimeout(() => setState('slow'), 10_000)
    return () => window.clearTimeout(id)
  }, [state])

  if (!draft) return <Navigate to="/report" replace />

  const weak = !moved && draft.fix?.accuracy != null && draft.fix.accuracy > WEAK_GPS_M

  async function saveForLater() {
    if (!draft) return
    await enqueue({
      id: newId(),
      photo: draft.photo,
      lat: pos[0],
      lon: pos[1],
      accuracy: moved ? null : (draft.fix?.accuracy ?? null),
      capturedAt: draft.capturedAt.toISOString(),
      note,
      source: 'citizen',
    })
    setSavedOffline(true)
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!draft) return
    setError(null)
    if (!navigator.onLine) {
      await saveForLater()
      return
    }
    setState('sending')
    try {
      const result = await submitReport({
        photo: draft.photo,
        lat: pos[0],
        lon: pos[1],
        accuracy: moved ? null : (draft.fix?.accuracy ?? null),
        capturedAt: draft.capturedAt,
        note,
      })
      setDraft(null)
      navigate(`/report/result/${result.tracking_code}`, { state: { result } })
    } catch (err) {
      setState('idle')
      const apiErr = err instanceof ApiError ? err : new ApiError('network', 0, String(err))
      if (apiErr.code === 'network') await saveForLater()
      else setError(apiErr)
    }
  }

  if (savedOffline) {
    return (
      <section className="flex flex-col gap-5">
        <Alert tone="info">{t('outbox.saved')}</Alert>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            setDraft(null)
            navigate('/')
          }}
        >
          {t('app.ok')}
        </button>
      </section>
    )
  }

  const errorText = error ? t(ERROR_KEYS[error.code], { area: PILOT_AREA_NAME }) : null
  const retake = error?.code === 'image_too_dark' || error?.code === 'invalid_image'

  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => void onSubmit(e)}>
      <h1 className="text-2xl font-bold">{t('review.title')}</h1>
      <img src={draft.previewUrl} alt={t('review.photoAlt')} className="max-h-72 w-full rounded-xl object-cover" />

      <div className="flex flex-col gap-2">
        <p className="font-medium">{t('review.pinHint')}</p>
        {draft.locationError && !moved && <Alert tone="warning">{t('errors.locationBlocked')}</Alert>}
        {weak && <Alert tone="warning">{t('errors.weakGps')}</Alert>}
        <PinMap lat={pos[0]} lon={pos[1]} onMove={onMove} label={t('review.pinHint')} />
      </div>

      <div>
        <label htmlFor="note" className="label">
          {t('review.noteLabel')}
        </label>
        <textarea
          id="note"
          className="input min-h-20"
          maxLength={200}
          placeholder={t('review.notePlaceholder')}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          aria-describedby="note-count"
        />
        <p id="note-count" className="mt-1 text-sm text-slate-600">
          {t('review.noteCount', { count: note.length })}
        </p>
      </div>

      <p className="text-sm text-slate-700">{t('review.privacy')}</p>

      {errorText && (
        <Alert
          tone="error"
          action={
            retake ? (
              <button type="button" className="btn btn-secondary" onClick={() => navigate('/report')}>
                {t('buttons.retakePhoto')}
              </button>
            ) : undefined
          }
        >
          {errorText}
        </Alert>
      )}
      {state !== 'idle' && (
        <div aria-live="polite" className="flex flex-col gap-2">
          <p className="font-medium">{state === 'slow' ? t('uploading.slow') : t('uploading.progress')}</p>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-brand-600" />
          </div>
        </div>
      )}

      <button type="submit" className="btn btn-primary min-h-14 text-lg" disabled={state !== 'idle'}>
        {t('review.submit')}
      </button>
      <button type="button" className="btn btn-secondary" onClick={() => navigate('/report')}>
        {t('review.retake')}
      </button>
    </form>
  )
}
