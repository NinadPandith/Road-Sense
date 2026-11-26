import { defineConfig, devices } from '@playwright/test'

// E2E tests mock the API and Supabase, so they need only the Vite dev server.
// Locally, PW_CHROMIUM can point at an existing Chromium; in CI run `pnpm exec playwright install chromium`.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: 'http://localhost:5174',
    trace: 'off',
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  projects: [
    { name: 'phone', use: { ...devices['Pixel 7'], launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {} }, testMatch: /citizen/ },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {} }, testMatch: /admin/ },
  ],
  webServer: {
    command: 'pnpm exec vite --port 5174 --strictPort',
    port: 5174,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_API_URL: 'http://api.test',
      VITE_SUPABASE_URL: 'http://supabase.test',
      VITE_SUPABASE_ANON_KEY: 'anon',
    },
  },
})
