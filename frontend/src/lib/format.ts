// Dates, numbers and distances, formatted with Intl (Content Guidelines, "Writing rules").

const LOCALE = 'en-IN'
const TZ = 'Asia/Kolkata'

// Day, three-letter month and year in IST. Built from parts because en-GB writes "Sept".
function dateParts(d: Date): { day: string; month: string; year: string } {
  const parts = new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: TZ,
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return { day: get('day'), month: get('month'), year: get('year') }
}

/** 27 Nov 2026 */
export function formatDate(iso: string | Date): string {
  const { day, month, year } = dateParts(typeof iso === 'string' ? new Date(iso) : iso)
  return `${day} ${month} ${year}`
}

/** 27 Nov (no year), for status lines */
export function formatShortDate(iso: string | Date): string {
  const { day, month } = dateParts(typeof iso === 'string' ? new Date(iso) : iso)
  return `${day} ${month}`
}

/** 6:30 pm */
export function formatTime(iso: string | Date): string {
  const d = typeof iso === 'string' ? new Date(iso) : iso
  return new Intl.DateTimeFormat('en-GB', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: TZ,
  })
    .format(d)
    .replace(/\s?(AM|PM)$/i, (m) => ` ${m.trim().toLowerCase()}`)
}

/** 2 h ago · Yesterday · 12 Nov 2026 (relative under 7 days, then a date) */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  const s = Math.round((now.getTime() - d.getTime()) / 1000)
  if (s < 60) return 'Just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  const days = Math.floor(s / 86400)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return formatDate(d)
}

/** 1,240 (comma every 3 digits, no lakh/crore) */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

/** 5 m under 1 km, 4.2 km above */
export function formatDistance(metres: number): string {
  if (metres < 1000) return `${Math.round(metres)} m`
  return `${(metres / 1000).toFixed(1)} km`
}

/** 0.82 */
export function formatScore(n: number | null | undefined): string {
  return n === null || n === undefined ? '–' : n.toFixed(2)
}

export { LOCALE }
