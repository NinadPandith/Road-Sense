import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert } from '../../components/Alert'
import { ApiError, ERROR_KEYS } from '../../lib/api'
import { getSettings, saveSettings, settingsHistory } from '../../lib/admin'
import { useAuth } from '../../lib/auth'
import { formatDate, formatTime } from '../../lib/format'
import type { ScoringSettings } from '../../lib/types'

/** A7 Settings: severity/priority weights, thresholds, merge radius. Every save is a new
 * version (logged) and recalculates all open priorities. */
export default function SettingsPage() {
  const { t } = useTranslation()
  const q = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  if (q.error) return <Alert tone="error">{t('errors.loadFailed')}</Alert>
  if (!q.data) return <p>{t('app.loading')}</p>
  return <SettingsForm initial={q.data} />
}

type NumField = { path: string[]; label: string; min: number; max: number; step: number }

function get(o: ScoringSettings, path: string[]): number {
  return path.reduce<unknown>((acc, k) => (acc as Record<string, unknown>)[k], o) as number
}
function set(o: ScoringSettings, path: string[], v: number): ScoringSettings {
  const copy = structuredClone(o)
  let cur = copy as unknown as Record<string, unknown>
  for (const k of path.slice(0, -1)) cur = cur[k] as Record<string, unknown>
  cur[path[path.length - 1]] = v
  return copy
}

function SettingsForm({ initial }: { initial: ScoringSettings }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { isEngineer } = useAuth()
  const [v, setV] = useState(initial)
  const [saved, setSaved] = useState(false)
  const history = useQuery({ queryKey: ['settings', 'history'], queryFn: settingsHistory })
  const save = useMutation({
    mutationFn: () => saveSettings(v),
    onSuccess: () => {
      setSaved(true)
      void qc.invalidateQueries({ queryKey: ['settings'] })
      void qc.invalidateQueries({ queryKey: ['defects'] })
    },
  })

  const w = v.severity_weights
  const weightSum = Math.round((w.A + w.D + w.T + w.P) * 100) / 100
  const thresholdsOk = v.thresholds.moderate < v.thresholds.dangerous

  const groups: { title: string; fields: NumField[] }[] = [
    {
      title: t('settings.severityWeights'),
      fields: (['A', 'D', 'T', 'P'] as const).map((k) => ({ path: ['severity_weights', k], label: t(`settings.weight.${k}`), min: 0, max: 1, step: 0.05 })),
    },
    {
      title: t('settings.thresholds'),
      fields: [
        { path: ['thresholds', 'moderate'], label: t('settings.moderateFrom'), min: 0, max: 1, step: 0.05 },
        { path: ['thresholds', 'dangerous'], label: t('settings.dangerousFrom'), min: 0, max: 1, step: 0.05 },
      ],
    },
    {
      title: t('settings.typeWeights'),
      fields: (['pothole', 'alligator_crack', 'crack_across', 'crack_along'] as const).map((k) => ({ path: ['type_weights', k], label: t(`damage.${k}`), min: 0, max: 1, step: 0.05 })),
    },
    {
      title: t('settings.roadWeights'),
      fields: (['major', 'secondary', 'tertiary', 'residential', 'unknown'] as const).map((k) => ({ path: ['road_weights', k], label: t(`road.${k}`), min: 0, max: 1, step: 0.05 })),
    },
    {
      title: t('settings.mergingAndPriority'),
      fields: [
        { path: ['merge_radius_m'], label: t('settings.mergeRadius'), min: 1, max: 50, step: 1 },
        { path: ['min_confidence'], label: t('settings.minConfidence'), min: 0.05, max: 0.95, step: 0.05 },
        { path: ['sensitive_radius_m'], label: t('settings.sensitiveRadius'), min: 50, max: 2000, step: 10 },
        { path: ['sensitive_boost'], label: t('settings.sensitiveBoost'), min: 1, max: 3, step: 0.1 },
        { path: ['auto_verify_reports'], label: t('settings.autoVerify'), min: 2, max: 50, step: 1 },
        { path: ['reopen_days'], label: t('settings.reopenDays'), min: 0, max: 365, step: 1 },
      ],
    },
  ]

  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={(e) => {
        e.preventDefault()
        setSaved(false)
        save.mutate()
      }}
    >
      <h1 className="text-2xl font-bold">{t('admin.nav.settings')}</h1>
      <p className="text-slate-700">{t('settings.intro')}</p>
      <div className="grid gap-5 lg:grid-cols-2">
        {groups.map((g) => (
          <fieldset key={g.title} className="card flex flex-col gap-3" disabled={!isEngineer}>
            <legend className="sr-only">{g.title}</legend>
            <h2 className="text-lg font-semibold" aria-hidden="true">{g.title}</h2>
            {g.fields.map((f) => {
              const id = f.path.join('-')
              return (
                <div key={id} className="grid grid-cols-[1fr_7rem] items-center gap-3">
                  <label htmlFor={id}>{f.label}</label>
                  <input
                    id={id}
                    type="number"
                    className="input tabular-nums"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={get(v, f.path)}
                    onChange={(e) => setV(set(v, f.path, Number(e.target.value)))}
                  />
                </div>
              )
            })}
            {g.fields[0].path[0] === 'severity_weights' && (
              <p className={weightSum === 1 ? 'text-sm text-slate-600' : 'text-sm font-medium text-amber-800'}>
                {t('settings.weightSum', { sum: weightSum.toFixed(2) })}
              </p>
            )}
          </fieldset>
        ))}
      </div>
      {!thresholdsOk && <Alert tone="warning">{t('settings.thresholdOrder')}</Alert>}
      {saved && <Alert tone="success">{t('settings.saved')}</Alert>}
      {save.error && <Alert tone="error">{t(save.error instanceof ApiError ? ERROR_KEYS[save.error.code] : 'errors.generic')}</Alert>}
      {isEngineer ? (
        <button type="submit" className="btn btn-primary self-start" disabled={save.isPending || weightSum !== 1 || !thresholdsOk}>
          {t('settings.save')}
        </button>
      ) : (
        <p className="text-slate-600">{t('errors.demoReadOnly')}</p>
      )}
      <section className="card">
        <h2 className="mb-2 text-lg font-semibold">{t('settings.history')}</h2>
        <ol className="flex flex-col gap-1 text-sm">
          {history.data?.map((h) => (
            <li key={h.id}>
              {t('settings.version', { id: h.id })} · {h.created_by ?? t('admin.detail.system')} · {formatDate(h.created_at)}, {formatTime(h.created_at)}
            </li>
          ))}
        </ol>
      </section>
    </form>
  )
}
