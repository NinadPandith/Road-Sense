import { useTranslation } from 'react-i18next'

export function Placeholder({ title, message }: { title: string; message?: string }) {
  const { t } = useTranslation()
  return (
    <section>
      <h1 className="mb-3 text-2xl font-bold">{title}</h1>
      <p className="card text-slate-700">{message ?? t('admin.comingSoon')}</p>
    </section>
  )
}
