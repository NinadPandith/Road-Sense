import { useTranslation } from 'react-i18next'
import type { SeverityFactors } from '../lib/types'

const ORDER: (keyof SeverityFactors)[] = ['size', 'depth', 'type', 'position']

export function level(v: number | null): 'low' | 'medium' | 'high' | 'unknown' {
  if (v === null) return 'unknown'
  if (v >= 0.67) return 'high'
  if (v >= 0.34) return 'medium'
  return 'low'
}

/** Four bars: Size, Depth, Damage type, Position on road. Citizens see Low/Medium/High;
 * engineers also see the number. */
export function FactorBars({ factors, showNumbers = false }: { factors: SeverityFactors; showNumbers?: boolean }) {
  const { t } = useTranslation()
  return (
    <ul className="space-y-3">
      {ORDER.map((k) => {
        const v = factors[k]
        const lvl = level(v)
        return (
          <li key={k}>
            <div className="flex justify-between text-sm">
              <span className="font-medium text-slate-700">{t(`severity.factor.${k}`)}</span>
              <span className="text-slate-600">
                {t(`severity.level.${lvl}`)}
                {showNumbers && v !== null && <span className="ml-1 tabular-nums">({v.toFixed(2)})</span>}
              </span>
            </div>
            <div
              className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-200"
              role="meter"
              aria-label={t(`severity.factor.${k}`)}
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={v ?? 0}
              aria-valuetext={t(`severity.level.${lvl}`)}
            >
              <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.round((v ?? 0) * 100)}%` }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
