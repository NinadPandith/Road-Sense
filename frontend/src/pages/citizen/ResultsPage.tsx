import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { formatDate, formatNumber } from '../../lib/format'

// Shapes written by ml/scripts/build_results_json.py (null until an experiment has run).
interface ModelRow {
  model: string
  map50: number
  map50_95: number
  per_class: Record<string, { precision: number; recall: number; map50: number }>
  cpu_fps_onnx: number
  size_mb: number
  test_images: number
}
interface SeverityMetrics {
  n: number
  accuracy: number
  kappa_linear: number
  confusion_matrix: number[][]
}
interface Results {
  generated_at: string
  e1: { split: string; models: ModelRow[] } | null
  e2: { models: ModelRow[] } | null
  e3: {
    prd_weights: Record<string, number>
    tuned_weights: Record<string, number>
    held_out_half: { prd_weights: SeverityMetrics; tuned_weights: SeverityMetrics }
    all_data_prd: SeverityMetrics
  } | null
  e4: { ablation: { variant: string; kappa_linear: number; change: number }[] } | null
  e5: {
    before: { reports: number; real_potholes: number }
    sweep: { eps_m: number; clusters: number; merge_accuracy: number; duplicates_left: number; wrongly_merged: number }[]
    chosen_eps_m: number
  } | null
  e6: {
    runs: {
      label: string
      detector_cpu_fps?: number
      depth_cpu_fps?: number
      photo_report?: { median_s: number; p90_s: number }
      video?: { sampled_fps: number }
    }[]
  } | null
  figures: Record<string, string>
}

const pct = (v: number) => `${Math.round(v * 100)}%`
const n2 = (v: number) => v.toFixed(2)

/** P8 Results: real numbers, with test-set sizes and failure cases (Content Guidelines). */
export default function ResultsPage() {
  const { t } = useTranslation()
  const q = useQuery({
    queryKey: ['results'],
    queryFn: async () => {
      const res = await fetch('/results/results.json')
      if (!res.ok) return null
      return (await res.json()) as Results
    },
    staleTime: Infinity,
  })
  const r = q.data
  const pending = <p className="text-slate-600">{t('results.pending')}</p>

  const potholeLine = (() => {
    const small = r?.e1?.models.find((m) => m.model.includes('11s')) ?? r?.e1?.models[0]
    if (!small) return null
    return t('results.headline', {
      map: n2(small.per_class.pothole?.map50 ?? small.map50),
      images: formatNumber(small.test_images),
    })
  })()

  return (
    <section className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-bold">{t('results.title')}</h1>
        <p className="mt-2 text-lg text-slate-700">{t('results.intro')}</p>
        {potholeLine && <p className="mt-2 text-lg font-semibold">{potholeLine}</p>}
        {r?.generated_at && <p className="mt-1 text-sm text-slate-600">{t('results.updated', { date: formatDate(r.generated_at) })}</p>}
      </div>

      <Section title={t('results.e1')} question={t('results.e1q')}>
        {r?.e1 ? (
          <Table
            caption={t('results.e1')}
            head={[t('results.model'), 'mAP@0.5', 'mAP@0.5:0.95', t('results.potholeAp'), t('results.cpuFps'), t('results.sizeMb')]}
            rows={r.e1.models.map((m) => [m.model, n2(m.map50), n2(m.map50_95), n2(m.per_class.pothole?.map50 ?? 0), m.cpu_fps_onnx.toFixed(1), m.size_mb.toFixed(1)])}
            note={t('results.testImages', { count: r.e1.models[0]?.test_images ?? 0 })}
          />
        ) : pending}
      </Section>

      <Section title={t('results.e2')} question={t('results.e2q')}>
        {r?.e2 ? (
          <Table
            caption={t('results.e2')}
            head={[t('results.training'), 'mAP@0.5', t('results.potholeAp')]}
            rows={r.e2.models.map((m) => [m.model === 'rdd_only' ? t('results.rddOnly') : m.model === 'rdd_plus_local' ? t('results.rddLocal') : m.model, n2(m.map50), n2(m.per_class.pothole?.map50 ?? 0)])}
            note={t('results.testImages', { count: r.e2.models[0]?.test_images ?? 0 })}
          />
        ) : pending}
      </Section>

      <Section title={t('results.e3')} question={t('results.e3q')}>
        {r?.e3 ? (
          <>
            <Table
              caption={t('results.e3')}
              head={[t('results.weights'), t('results.testN'), t('results.accuracy'), t('results.kappa')]}
              rows={[
                [t('results.prdWeights'), r.e3.held_out_half.prd_weights.n, pct(r.e3.held_out_half.prd_weights.accuracy), n2(r.e3.held_out_half.prd_weights.kappa_linear)],
                [t('results.tunedWeights'), r.e3.held_out_half.tuned_weights.n, pct(r.e3.held_out_half.tuned_weights.accuracy), n2(r.e3.held_out_half.tuned_weights.kappa_linear)],
              ]}
            />
            {r.figures.e3_confusion && <img src={r.figures.e3_confusion} alt={t('results.confusionAlt')} className="max-w-sm rounded-lg" />}
          </>
        ) : pending}
      </Section>

      <Section title={t('results.e4')} question={t('results.e4q')}>
        {r?.e4 ? (
          <Table
            caption={t('results.e4')}
            head={[t('results.variant'), t('results.kappa'), t('results.change')]}
            rows={r.e4.ablation.map((a) => [a.variant, n2(a.kappa_linear), a.change === 0 ? '–' : (a.change > 0 ? '+' : '') + n2(a.change)])}
          />
        ) : pending}
      </Section>

      <Section title={t('results.e5')} question={t('results.e5q')}>
        {r?.e5 ? (
          <Table
            caption={t('results.e5')}
            head={[t('results.radius'), t('results.clusters'), t('results.mergeAccuracy'), t('results.duplicates'), t('results.wrongMerges')]}
            rows={r.e5.sweep.map((s) => [`${s.eps_m} m`, s.clusters, pct(s.merge_accuracy), s.duplicates_left, s.wrongly_merged])}
            note={t('results.mergeNote', { reports: r.e5.before.reports, potholes: r.e5.before.real_potholes })}
          />
        ) : pending}
      </Section>

      <Section title={t('results.e6')} question={t('results.e6q')}>
        {r?.e6 ? (
          <Table
            caption={t('results.e6')}
            head={[t('results.machine'), t('results.photoSeconds'), t('results.detectorFps'), t('results.videoFps')]}
            rows={r.e6.runs.map((x) => [x.label, x.photo_report ? x.photo_report.median_s.toFixed(1) : '–', x.detector_cpu_fps?.toFixed(1) ?? '–', x.video?.sampled_fps.toFixed(1) ?? '–'])}
          />
        ) : pending}
      </Section>

      <Section title={t('results.failures')} question={t('results.failuresNote')}>
        {r?.figures.failure_grid ? (
          <img src={r.figures.failure_grid} alt={t('results.failuresAlt')} className="w-full rounded-lg" />
        ) : pending}
      </Section>
    </section>
  )
}

function Section({ title, question, children }: { title: string; question: string; children: ReactNode }) {
  return (
    <section className="card flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-slate-700">{question}</p>
      </div>
      {children}
    </section>
  )
}

function Table({ caption, head, rows, note }: { caption: string; head: string[]; rows: (string | number)[][]; note?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="text-slate-700">
          <tr>{head.map((h) => <th key={h} className="py-1.5 pr-4 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-slate-100">
              {r.map((v, j) => <td key={j} className="py-1.5 pr-4 tabular-nums">{v}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {note && <p className="mt-2 text-sm text-slate-600">{note}</p>}
    </div>
  )
}
