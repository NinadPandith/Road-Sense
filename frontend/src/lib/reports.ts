import { api } from './api'
import { resizeImage } from './image'
import { saveMyReport } from './myReports'
import type { ReportResult, TrackResult } from './types'

const RESULT_KEY = (code: string) => `roadsense.result.${code}`

export interface NewReport {
  photo: Blob
  lat: number
  lon: number
  accuracy: number | null
  capturedAt: Date
  note: string
  source?: 'citizen' | 'drive'
}

function newId(): string {
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
        (+c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))).toString(16),
      )
}

export async function submitReport(r: NewReport): Promise<ReportResult> {
  const form = new FormData()
  form.append('image', await resizeImage(r.photo), 'photo.jpg')
  form.append('lat', r.lat.toFixed(7))
  form.append('lon', r.lon.toFixed(7))
  if (r.accuracy !== null) form.append('accuracy_m', String(Math.round(r.accuracy)))
  form.append('captured_at', r.capturedAt.toISOString())
  form.append('source', r.source ?? 'citizen')
  form.append('client_report_id', newId())
  if (r.note.trim()) form.append('note', r.note.trim())
  const result = await api<ReportResult>('/reports', { form })
  rememberResult(result)
  return result
}

export function rememberResult(result: ReportResult): void {
  saveMyReport({
    code: result.tracking_code,
    createdAt: new Date().toISOString(),
    thumbUrl: result.thumb_url,
  })
  try {
    sessionStorage.setItem(RESULT_KEY(result.tracking_code), JSON.stringify(result))
  } catch {
    /* ignore */
  }
}

export function recallResult(code: string): ReportResult | null {
  try {
    const raw = sessionStorage.getItem(RESULT_KEY(code))
    return raw ? (JSON.parse(raw) as ReportResult) : null
  } catch {
    return null
  }
}

export function sendAnyway(code: string): Promise<ReportResult> {
  return api<ReportResult>(`/reports/${encodeURIComponent(code)}/send-anyway`, { method: 'POST' }).then(
    (r) => {
      rememberResult(r)
      return r
    },
  )
}

export function track(code: string): Promise<TrackResult> {
  return api<TrackResult>(`/track/${encodeURIComponent(code)}`)
}
