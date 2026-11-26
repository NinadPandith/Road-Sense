// Error tracking (D4). Loaded only when a DSN is configured, so it costs nothing otherwise.
// No personal data: no IPs, and the tracking code / GPS stay out of breadcrumbs.
export function initSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return
  void import('@sentry/react').then((Sentry) =>
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
      tracesSampleRate: 0.05,
      beforeBreadcrumb: (b) => (b.category === 'fetch' || b.category === 'xhr' ? null : b),
    }),
  )
}
