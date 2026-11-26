import { api, apiBlob, apiUpload } from './api'
import type {
  DamageClass,
  DefectDetail,
  DefectListItem,
  DefectStatus,
  Page,
  RoadClass,
  ScoringSettings,
  SettingsVersion,
  SeverityLabel,
  Stats,
  Survey,
} from './types'

export interface Filters {
  status?: DefectStatus[]
  severity?: SeverityLabel[]
  ward_id?: string[]
  road_class?: RoadClass[]
  survey_id?: string
  from?: string
  to?: string
  sort?: string
}

export function filterQuery(f: Filters) {
  return {
    status: f.status,
    severity: f.severity,
    ward_id: f.ward_id,
    road_class: f.road_class,
    survey_id: f.survey_id,
    from: f.from,
    to: f.to,
    sort: f.sort,
  }
}

export function listDefects(f: Filters, page = 1, pageSize = 50) {
  return api<Page<DefectListItem>>('/defects', {
    auth: true,
    query: { ...filterQuery(f), page, page_size: pageSize },
  })
}

/** All matching defects (up to `max`) for maps, fetched 100 at a time. */
export async function allDefects(f: Filters, max = 1000): Promise<DefectListItem[]> {
  const out: DefectListItem[] = []
  for (let page = 1; out.length < max; page++) {
    const res = await listDefects(f, page, 100)
    out.push(...res.items)
    if (out.length >= res.total || res.items.length === 0) break
  }
  return out
}

export function getDefect(id: string) {
  return api<DefectDetail>(`/defects/${id}`, { auth: true })
}

export function changeStatus(
  id: string,
  to: DefectStatus,
  reason?: string,
  photo?: File | null,
  review?: { damageClass?: DamageClass; severity?: SeverityLabel },
) {
  const form = new FormData()
  form.append('to_status', to)
  if (reason) form.append('reason', reason)
  if (photo) form.append('fixed_photo', photo)
  if (review?.damageClass) form.append('damage_class', review.damageClass)
  if (review?.severity) form.append('severity_label', review.severity)
  return api<DefectDetail>(`/defects/${id}/status`, { method: 'PATCH', form, auth: true })
}

export function bulkStatus(ids: string[], to: DefectStatus) {
  return api<{ updated: number; skipped: string[] }>('/defects/bulk-status', {
    json: { ids, to_status: to },
    auth: true,
  })
}

export function getStats(from?: string) {
  return api<Stats>('/stats', { auth: true, query: { from } })
}

export function listSurveys() {
  return api<Survey[]>('/surveys', { auth: true })
}

export function uploadSurvey(name: string, video: File, gpx: File, onProgress: (f: number) => void) {
  const form = new FormData()
  form.append('name', name)
  form.append('video', video)
  form.append('gpx', gpx)
  return apiUpload<Survey>('/surveys', form, onProgress)
}

export function getSettings() {
  return api<ScoringSettings>('/settings', { auth: true })
}

export function saveSettings(values: ScoringSettings) {
  return api<ScoringSettings>('/settings', { json: values, auth: true })
}

export function settingsHistory() {
  return api<SettingsVersion[]>('/settings/history', { auth: true })
}

export async function downloadCsv(f: Filters) {
  const blob = await apiBlob('/repair-list.csv', { auth: true, query: filterQuery(f) })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `roadsense-repair-list-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export const NEXT_ACTIONS: Record<DefectStatus, DefectStatus[]> = {
  needs_review: ['reported', 'rejected'],
  reported: ['verified', 'assigned', 'rejected'],
  verified: ['assigned', 'rejected'],
  assigned: ['fixed', 'rejected'],
  fixed: [],
  rejected: [],
}
