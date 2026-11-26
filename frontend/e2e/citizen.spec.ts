import { expect, test } from '@playwright/test'
import { API, blockTiles, expectAccessible, reportResult, track } from './fixtures'

// A small valid JPEG for the file input.
const JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=',
  'base64',
)

test.beforeEach(async ({ page, context }) => {
  await blockTiles(page)
  await context.grantPermissions(['geolocation'])
  await context.setGeolocation({ latitude: 12.9716, longitude: 77.5946, accuracy: 10 })
})

test('report a pothole: capture, review, result, track', async ({ page }) => {
  let posted: string | null = null
  await page.route(`${API}/reports`, async (route) => {
    posted = route.request().postData() ?? ''
    await route.fulfill({ json: reportResult })
  })
  await page.route(`${API}/track/RS-7K2Q`, (route) => route.fulfill({ json: track }))

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Spotted a pothole?' })).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('link', { name: 'Report a pothole' }).first().click()
  await expectAccessible(page)
  await page.locator('input[type=file]').nth(1).setInputFiles({ name: 'p.jpg', mimeType: 'image/jpeg', buffer: JPEG })

  await expect(page.getByRole('heading', { name: 'Check your report' })).toBeVisible()
  await page.getByLabel('Add a note (optional)').fill('near the bus stop')
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Submit report' }).click()

  await expect(page.getByRole('heading', { name: 'Thanks! Added to an existing report.' })).toBeVisible()
  expect(posted).toContain('near the bus stop')
  expect(posted).toContain('client_report_id')
  await expect(page.getByText('Dangerous because it is large, looks deep and in the wheel path.')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('link', { name: 'Track this report' }).click()
  await expect(page.getByText('An engineer confirmed this pothole.')).toBeVisible()
  await expectAccessible(page)

  await page.goto('/track')
  await expect(page.getByRole('link', { name: /RS-7K2Q/ })).toBeVisible()
})

test('offline report waits in the outbox and sends when back online', async ({ page, context }) => {
  let calls = 0
  await page.route(`${API}/reports`, async (route) => {
    calls++
    await route.fulfill({ json: reportResult })
  })
  await page.goto('/report')
  await page.locator('input[type=file]').nth(1).setInputFiles({ name: 'p.jpg', mimeType: 'image/jpeg', buffer: JPEG })
  await expect(page.getByRole('heading', { name: 'Check your report' })).toBeVisible()
  await context.setOffline(true)
  await page.getByRole('button', { name: 'Submit report' }).click()
  await expect(page.getByText("You're offline. We'll send your report when you're back online.")).toBeVisible()
  expect(calls).toBe(0)
  await context.setOffline(false)
  await expect.poll(() => calls).toBe(1)
})

test('wrong tracking code and rate limit messages', async ({ page }) => {
  await page.route(`${API}/track/RS-ZZZZ`, (r) =>
    r.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'x' } } }),
  )
  await page.goto('/track/RS-ZZZZ')
  await expect(page.getByText('No report found with this code. Check it and try again.')).toBeVisible()

  await page.route(`${API}/reports`, (r) =>
    r.fulfill({ status: 429, json: { error: { code: 'rate_limited', message: 'x', retry_after_s: 3600 } } }),
  )
  await page.goto('/report')
  await page.locator('input[type=file]').nth(1).setInputFiles({ name: 'p.jpg', mimeType: 'image/jpeg', buffer: JPEG })
  await page.getByRole('button', { name: 'Submit report' }).click()
  await expect(page.getByText('Too many reports from this network. Please try again in an hour.')).toBeVisible()
})

test('other public screens are accessible', async ({ page }) => {
  await page.route(/supabase\.test/, (r) => r.fulfill({ json: [] }))
  for (const [path, text] of [
    ['/map', 'Reported potholes'],
    ['/results', 'How well RoadSense works'],
    ['/drive', "Mount your phone before you ride. Don't touch it while moving."],
  ]) {
    await page.goto(path)
    await expect(page.getByText(text).first()).toBeVisible()
    await expectAccessible(page)
  }
})
