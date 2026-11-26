import { expect, test, type Page } from '@playwright/test'
import { API, SUPABASE, blockTiles, defect, expectAccessible } from './fixtures'

const USER = { id: 'u1', aud: 'authenticated', role: 'authenticated', email: 'eng@x', app_metadata: {}, user_metadata: {}, created_at: '2026-11-01T00:00:00Z' }

async function mockBackend(page: Page, role: 'engineer' | 'demo' = 'engineer') {
  await blockTiles(page)
  await page.route(`${SUPABASE}/**`, (route) => {
    const url = route.request().url()
    if (url.includes('/auth/v1/token')) {
      const body = JSON.parse(route.request().postData() ?? '{}')
      if (body.password !== 'right')
        return route.fulfill({ status: 400, json: { error: 'invalid_grant', error_description: 'Invalid login credentials' } })
      return route.fulfill({
        json: { access_token: 'jwt', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600, refresh_token: 'r', user: USER },
      })
    }
    if (url.includes('/realtime/')) return route.abort()
    return route.fulfill({ json: [] })
  })
  const detail = {
    ...defect,
    priority_terms: { S: 0.82, R: 1, n: 4, t: 12, B: 1.3 },
    sensitive_place: 'school: Govt School',
    reopened_count: 0,
    fixed_at: null,
    fixed_photo_url: null,
    merge_radius_m: 5,
    reports: [],
    history: [{ from_status: null, to_status: 'reported', changed_by: null, reason: 'first report', created_at: '2026-11-15T04:12:00Z' }],
  }
  const settings = {
    severity_weights: { A: 0.35, D: 0.35, T: 0.2, P: 0.1 },
    thresholds: { moderate: 0.4, dangerous: 0.7 },
    type_weights: { pothole: 1, alligator_crack: 0.7, crack_across: 0.5, crack_along: 0.4 },
    road_weights: { major: 1, secondary: 0.8, tertiary: 0.6, residential: 0.4, unknown: 0.5 },
    merge_radius_m: 5, min_confidence: 0.35, sensitive_radius_m: 200, sensitive_boost: 1.3, auto_verify_reports: 3, reopen_days: 30,
  }
  await page.route(`${API}/**`, (route) => {
    const u = new URL(route.request().url())
    const method = route.request().method()
    if (u.pathname === '/me') return route.fulfill({ json: { id: 'u1', full_name: 'Test Engineer', role } })
    if (u.pathname === '/stats')
      return route.fulfill({
        json: {
          open_defects: 24, dangerous_open: 6, new_this_week: 5, fixed_this_week: 3, needs_review: 2,
          open_by_severity: [{ key: 'dangerous', count: 6 }, { key: 'moderate', count: 10 }, { key: 'minor', count: 8 }],
          open_by_ward: [{ key: 'Ward 112', count: 14 }, { key: 'Ward 113', count: 10 }],
          per_week: [{ week_start: '2026-11-16', reported: 9, fixed: 2 }, { week_start: '2026-11-23', reported: 5, fixed: 3 }],
        },
      })
    if (u.pathname === '/defects') return route.fulfill({ json: { items: [defect], total: 1, page: 1, page_size: 50 } })
    if (u.pathname === '/defects/d1/status' && method === 'PATCH')
      return route.fulfill({ json: { ...detail, status: 'assigned', history: [{ from_status: 'verified', to_status: 'assigned', changed_by: 'Test Engineer', reason: null, created_at: '2026-11-28T04:00:00Z' }, ...detail.history] } })
    if (u.pathname === '/defects/d1') return route.fulfill({ json: detail })
    if (u.pathname === '/surveys')
      return route.fulfill({
        json: [{ id: 's1', name: 'Morning ride', status: 'done', progress: 100, frames_total: 400, detections_count: 38, defects_new: 9, defects_merged: 12, error: null, created_at: '2026-11-27T02:00:00Z', started_at: null, finished_at: null }],
      })
    if (u.pathname === '/settings/history') return route.fulfill({ json: [{ id: 1, created_at: '2026-11-20T00:00:00Z', created_by: null, values: settings }] })
    if (u.pathname === '/settings') return route.fulfill({ json: settings })
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'x' } } })
  })
}

async function signIn(page: Page, password = 'right') {
  await page.goto('/admin/login')
  await page.getByLabel('Email').fill('eng@x')
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

test('engineer signs in, sees the ranked list and assigns a repair', async ({ page }) => {
  await mockBackend(page)
  await signIn(page, 'wrong')
  await expect(page.getByText('Email or password is incorrect.')).toBeVisible()
  await expectAccessible(page)

  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Fix these first' })).toBeVisible()
  await expect(page.getByText('2 photos need your review')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('link', { name: 'Repair list' }).click()
  await expect(page.getByRole('cell', { name: '#1' })).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('link', { name: 'Pothole' }).click()
  await expect(page.getByRole('heading', { name: 'Why this priority' })).toBeVisible()
  await expectAccessible(page)
  await page.getByText('Assign repair', { exact: true }).click()
  await page.getByRole('button', { name: 'Save status' }).click()
  await expect(page.getByText('Verified → Assigned')).toBeVisible()
})

test('surveys, analytics and settings screens', async ({ page }) => {
  await mockBackend(page)
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Fix these first' })).toBeVisible()
  for (const [link, text] of [
    ['Surveys', '38 potholes found → 21 defects (9 new, 12 added to existing)'],
    ['Analytics', 'Reported and fixed per week'],
    ['Settings', 'Change history'],
  ]) {
    await page.getByRole('link', { name: link }).click()
    await expect(page.getByText(text).first()).toBeVisible()
    await expectAccessible(page)
  }
})

test('demo account is read only', async ({ page }) => {
  await mockBackend(page, 'demo')
  await signIn(page)
  await expect(page.getByText("You're using the read-only demo account.")).toBeVisible()
  await page.goto('/admin/defects/d1')
  await expect(page.getByRole('heading', { name: 'Why this priority' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save status' })).toHaveCount(0)
})
