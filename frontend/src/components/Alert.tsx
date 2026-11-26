import clsx from 'clsx'
import type { ReactNode } from 'react'

/** Messages after an action are announced to screen readers (aria-live). */
export function Alert({
  tone = 'info',
  children,
  action,
}: {
  tone?: 'info' | 'warning' | 'error' | 'success'
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live={tone === 'error' ? 'assertive' : 'polite'}
      className={clsx(
        'rounded-xl border p-3 text-base',
        tone === 'info' && 'border-sky-200 bg-sky-50 text-sky-900',
        tone === 'warning' && 'border-amber-300 bg-amber-50 text-amber-900',
        tone === 'error' && 'border-red-300 bg-red-50 text-red-900',
        tone === 'success' && 'border-green-300 bg-green-50 text-green-900',
      )}
    >
      <p>{children}</p>
      {action && <div className="mt-2 flex flex-wrap gap-2">{action}</div>}
    </div>
  )
}
