import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import type { DefectStatus, SeverityLabel } from '../lib/types'
import { SeverityIcon } from './Icons'

const SEVERITY_STYLE: Record<SeverityLabel, string> = {
  minor: 'bg-green-50 text-minor ring-green-200',
  moderate: 'bg-amber-50 text-moderate ring-amber-200',
  dangerous: 'bg-red-50 text-dangerous ring-red-200',
}

/** Severity is always word + colour + icon, never colour alone. */
export function SeverityBadge({
  label,
  score,
  size = 'md',
}: {
  label: SeverityLabel | null
  score?: number | null
  size?: 'md' | 'lg'
}) {
  const { t } = useTranslation()
  if (!label)
    return (
      <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-sm font-medium text-slate-700 ring-1 ring-slate-200">
        {t('severity.unscored')}
      </span>
    )
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-semibold ring-1',
        SEVERITY_STYLE[label],
        size === 'lg' ? 'px-3.5 py-1.5 text-lg' : 'px-2.5 py-1 text-sm',
      )}
    >
      <SeverityIcon label={label} className={size === 'lg' ? 'h-5 w-5' : 'h-3.5 w-3.5'} />
      {t(`severity.${label}`)}
      {score !== undefined && score !== null && <span className="font-normal">({score.toFixed(2)})</span>}
    </span>
  )
}

const STATUS_STYLE: Record<DefectStatus, string> = {
  needs_review: 'bg-violet-50 text-violet-800 ring-violet-200',
  reported: 'bg-slate-100 text-slate-800 ring-slate-300',
  verified: 'bg-sky-50 text-sky-800 ring-sky-200',
  assigned: 'bg-amber-50 text-amber-800 ring-amber-200',
  fixed: 'bg-green-50 text-green-800 ring-green-200',
  rejected: 'bg-slate-50 text-slate-500 ring-slate-200',
}

export function StatusBadge({ status }: { status: DefectStatus }) {
  const { t } = useTranslation()
  return (
    <span className={clsx('inline-flex rounded-full px-2.5 py-1 text-sm font-medium ring-1', STATUS_STYLE[status])}>
      {t(`status.${status}`)}
    </span>
  )
}

export const SEVERITY_COLOURS: Record<SeverityLabel | 'none' | 'fixed', string> = {
  minor: '#15803d',
  moderate: '#d97706',
  dangerous: '#b91c1c',
  none: '#64748b',
  fixed: '#2563eb',
}
