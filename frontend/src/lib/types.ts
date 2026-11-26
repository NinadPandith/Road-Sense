// Shapes returned by the FastAPI backend (docs/backend-schema.md, "API schemas").

export type DamageClass = 'pothole' | 'alligator_crack' | 'crack_across' | 'crack_along'
export type SeverityLabel = 'minor' | 'moderate' | 'dangerous'
export type DefectStatus = 'needs_review' | 'reported' | 'verified' | 'assigned' | 'fixed' | 'rejected'
export type ReportStatus = 'processing' | 'done' | 'no_damage' | 'needs_review' | 'failed'
export type RoadClass = 'major' | 'secondary' | 'tertiary' | 'residential' | 'unknown'
export type ConfidenceLabel = 'very_likely' | 'likely' | 'possible'
export type Outcome = 'new' | 'merged' | 'no_damage' | 'needs_review' | 'processing'

export interface SeverityFactors {
  size: number
  depth: number | null
  type: number
  position: number
}

export interface Box {
  damage_class: DamageClass
  confidence: number
  box: number[]
}

export interface ReportResult {
  tracking_code: string
  status: ReportStatus
  outcome: Outcome
  defect_id: string | null
  report_count: number | null
  damage_class: DamageClass | null
  confidence_label: ConfidenceLabel | null
  severity: {
    label: SeverityLabel
    score: number
    factors: SeverityFactors
    reason: string
  } | null
  boxes: Box[]
  thumb_url: string | null
  image_url: string | null
}

export interface TrackResult {
  tracking_code: string
  report_status: ReportStatus
  created_at: string
  defect_status: DefectStatus | null
  damage_class: DamageClass | null
  severity_label: SeverityLabel | null
  report_count: number | null
  image_url: string | null
  thumb_url: string | null
  fixed_photo_url: string | null
  timeline: { status: DefectStatus; at: string | null }[]
}

export interface Ward {
  id: number
  name: string
}

export interface DefectListItem {
  id: string
  rank: number | null
  lat: number
  lon: number
  damage_class: DamageClass | null
  severity_label: SeverityLabel | null
  severity_score: number | null
  priority: number
  priority_reason: string
  road_class: RoadClass
  road_name: string | null
  ward: Ward | null
  report_count: number
  age_days: number
  status: DefectStatus
  near_sensitive: boolean
  first_reported_at: string
  thumb_url: string | null
}

export interface DetectionOut extends Box {
  size_score: number
  depth_score: number | null
  type_score: number
  position_score: number
  severity_score: number
  severity_label: SeverityLabel
}

export interface DefectDetail extends DefectListItem {
  priority_terms: { S?: number; R?: number; n?: number; t?: number; B?: number }
  sensitive_place: string | null
  reopened_count: number
  fixed_at: string | null
  fixed_photo_url: string | null
  merge_radius_m: number
  reports: {
    id: string
    tracking_code: string
    source: 'citizen' | 'drive' | 'survey'
    lat: number
    lon: number
    image_url: string | null
    note: string | null
    detections: DetectionOut[]
    created_at: string
  }[]
  history: {
    from_status: DefectStatus | null
    to_status: DefectStatus
    changed_by: string | null
    reason: string | null
    created_at: string
  }[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Stats {
  open_defects: number
  dangerous_open: number
  new_this_week: number
  fixed_this_week: number
  needs_review: number
  open_by_severity: { key: string; count: number }[]
  open_by_ward: { key: string; count: number }[]
  per_week: { week_start: string; fixed: number; reported: number }[]
}

export interface Me {
  id: string
  full_name: string
  role: 'engineer' | 'demo'
}

export type SurveyStatus = 'queued' | 'extracting' | 'detecting' | 'scoring' | 'merging' | 'done' | 'failed'

export interface Survey {
  id: string
  name: string
  status: SurveyStatus
  progress: number
  frames_total: number | null
  detections_count: number
  defects_new: number
  defects_merged: number
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  gpx_overlap?: boolean | null
}

export interface ScoringSettings {
  severity_weights: { A: number; D: number; T: number; P: number }
  thresholds: { moderate: number; dangerous: number }
  type_weights: Record<DamageClass, number>
  road_weights: Record<RoadClass, number>
  merge_radius_m: number
  min_confidence: number
  sensitive_radius_m: number
  sensitive_boost: number
  auto_verify_reports: number
  reopen_days: number
}

export interface SettingsVersion {
  id: number
  created_at: string
  created_by: string | null
  values: ScoringSettings
}
