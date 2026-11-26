import { useState } from 'react'
import { useTranslation } from 'react-i18next'

/** Tracking code shown large in monospace, with Copy and Share. */
export function CodeBox({ code }: { code: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const url = `${window.location.origin}/track/${code}`

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard blocked; the code is visible to copy by hand */
    }
  }

  async function share() {
    const text = `${t('result.shareText')} ${url}`
    if (navigator.share) {
      try {
        await navigator.share({ title: 'RoadSense', text, url })
      } catch {
        /* cancelled */
      }
    } else {
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
    }
  }

  return (
    <div className="rounded-2xl bg-brand-50 p-4 text-center">
      <p className="text-slate-700">{t('result.codeLabel')}</p>
      <p className="my-2 font-mono text-4xl font-bold tracking-wider text-brand-800">{code}</p>
      <div className="flex justify-center gap-2">
        <button type="button" className="btn btn-secondary" onClick={() => void copy()} aria-label={t('result.copyAria')}>
          {copied ? t('result.copied') : t('result.copy')}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void share()} aria-label={t('result.shareAria')}>
          {t('result.share')}
        </button>
      </div>
      <span className="sr-only" aria-live="polite">
        {copied ? t('result.copied') : ''}
      </span>
    </div>
  )
}
