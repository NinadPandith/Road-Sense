import { buildQuery } from '../lib/api'
import { formatDate, formatDistance, formatNumber, formatRelative, formatTime } from '../lib/format'
import { fitWithin } from '../lib/image'
import { level } from '../components/FactorBars'

describe('format (Content Guidelines writing rules)', () => {
  it('formats dates as 27 Nov 2026 in IST', () => {
    expect(formatDate('2026-11-27T04:00:00Z')).toBe('27 Nov 2026')
    expect(formatDate('2026-11-26T20:00:00Z')).toBe('27 Nov 2026') // 1:30 am IST next day
    expect(formatDate('2026-09-28T04:00:00Z')).toBe('28 Sep 2026') // never "Sept"
  })
  it('formats times as 6:30 pm', () => {
    expect(formatTime('2026-11-27T13:00:00Z')).toBe('6:30 pm')
  })
  it('formats distances: m under 1 km, km with one decimal', () => {
    expect(formatDistance(5)).toBe('5 m')
    expect(formatDistance(4200)).toBe('4.2 km')
  })
  it('uses commas every 3 digits, no lakh', () => {
    expect(formatNumber(1240)).toBe('1,240')
    expect(formatNumber(1234567)).toBe('1,234,567')
  })
  it('uses relative time under 7 days, then a date', () => {
    const now = new Date('2026-11-27T12:00:00Z')
    expect(formatRelative('2026-11-27T10:00:00Z', now)).toBe('2 h ago')
    expect(formatRelative('2026-11-26T10:00:00Z', now)).toBe('Yesterday')
    expect(formatRelative('2026-11-12T10:00:00Z', now)).toBe('12 Nov 2026')
  })
})

describe('api.buildQuery', () => {
  it('repeats array params and skips empty values', () => {
    expect(buildQuery({ status: ['reported', 'verified'], page: 2, ward: '', x: undefined })).toBe(
      '?status=reported&status=verified&page=2',
    )
  })
})

describe('image resize', () => {
  it('fits the long side to 1280 px', () => {
    expect(fitWithin(4000, 3000)).toEqual({ w: 1280, h: 960 })
    expect(fitWithin(800, 600)).toEqual({ w: 800, h: 600 })
  })
})

describe('factor levels', () => {
  it('maps scores to Low / Medium / High', () => {
    expect([level(0.1), level(0.5), level(0.9), level(null)]).toEqual(['low', 'medium', 'high', 'unknown'])
  })
})
