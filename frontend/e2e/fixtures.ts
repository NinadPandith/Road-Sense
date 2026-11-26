import AxeBuilder from '@axe-core/playwright'
import { expect, type Page } from '@playwright/test'

export const API = 'http://api.test'
export const SUPABASE = 'http://supabase.test'

export const reportResult = {
  tracking_code: 'RS-7K2Q',
  status: 'done',
  outcome: 'merged',
  defect_id: 'd1',
  report_count: 4,
  damage_class: 'pothole',
  confidence_label: 'very_likely',
  severity: {
    label: 'dangerous',
    score: 0.82,
    factors: { size: 0.74, depth: 0.88, type: 1, position: 0.9 },
    reason: 'large, looks deep and in the wheel path',
  },
  boxes: [{ damage_class: 'pothole', confidence: 0.91, box: [0.3, 0.5, 0.7, 0.9] }],
  thumb_url: null,
  image_url: null,
}

export const track = {
  tracking_code: 'RS-7K2Q',
  report_status: 'done',
  created_at: '2026-11-27T04:00:00Z',
  defect_status: 'verified',
  damage_class: 'pothole',
  severity_label: 'dangerous',
  report_count: 4,
  image_url: null,
  thumb_url: null,
  fixed_photo_url: null,
  timeline: [
    { status: 'reported', at: '2026-11-27T04:00:00Z' },
    { status: 'verified', at: '2026-11-28T06:00:00Z' },
    { status: 'assigned', at: null },
    { status: 'fixed', at: null },
  ],
}

export const defect = {
  id: 'd1',
  rank: 1,
  lat: 12.9716,
  lon: 77.5946,
  damage_class: 'pothole',
  severity_label: 'dangerous',
  severity_score: 0.82,
  priority: 2.71,
  priority_reason: 'Dangerous · main road · near school · 4 reports · 12 days open',
  road_class: 'major',
  road_name: 'MG Road',
  ward: { id: 12, name: 'Ward 112' },
  report_count: 4,
  age_days: 12,
  status: 'verified',
  near_sensitive: true,
  first_reported_at: '2026-11-15T04:12:00Z',
  thumb_url: null,
}

/** Fail on any serious or critical WCAG 2 A/AA violation. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .exclude('.leaflet-control-attribution')
    .analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([])
}

/** Block map tiles (no network in CI) so they don't slow tests down. */
export async function blockTiles(page: Page) {
  await page.route(/tile\.openstreetmap\.org/, (r) => r.abort())
}
