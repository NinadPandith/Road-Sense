export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL ?? ''
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''
export const PILOT_AREA_NAME = import.meta.env.VITE_PILOT_AREA_NAME ?? 'the pilot area'
export const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL ?? 'demo@roadsense.app'
export const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD ?? 'roadsense-demo'

/** Default map centre "lat,lon" when there is no GPS fix (Bengaluru unless configured). */
export const MAP_CENTER: [number, number] = (() => {
  const raw = import.meta.env.VITE_MAP_CENTER
  const parts = raw?.split(',').map(Number)
  return parts && parts.length === 2 && parts.every(Number.isFinite)
    ? [parts[0], parts[1]]
    : [12.9716, 77.5946]
})()

export const WEAK_GPS_M = 30
