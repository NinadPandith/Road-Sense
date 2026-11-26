// Content Guidelines checks on every UI string in en.json.
import en from '../locales/en.json'

function strings(obj: unknown, path = ''): [string, string][] {
  if (typeof obj === 'string') return [[path, obj]]
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) => strings(v, path ? `${path}.${k}` : k))
}

const all = strings(en)

describe('en.json copy rules', () => {
  it('has no exclamation marks except "Thanks!"', () => {
    const bad = all.filter(([, s]) => s.replace(/Thanks!/g, '').includes('!'))
    expect(bad).toEqual([])
  })

  it('has no emoji', () => {
    const bad = all.filter(([, s]) => /\p{Extended_Pictographic}/u.test(s))
    expect(bad).toEqual([])
  })

  it('has no ALL CAPS words except GPS, AI, PDF, CSV, file formats and codes', () => {
    const allowed = new Set(['GPS', 'AI', 'PDF', 'CSV', 'RS', 'ID', 'OK', 'JPEG', 'PNG'])
    const bad = all.filter(([, s]) =>
      (s.match(/\b[A-Z]{2,}\b/g) ?? []).some((w) => !allowed.has(w) && !/RS-/.test(s)),
    )
    expect(bad).toEqual([])
  })

  it('avoids banned terms (complaint, ticket, issue, Oops)', () => {
    const bad = all.filter(([, s]) => /\b(complaint|ticket|issue|oops)\b/i.test(s))
    expect(bad).toEqual([])
  })

  it('never promises a repair', () => {
    const bad = all.filter(([, s]) => /will be fixed|will fix/i.test(s))
    expect(bad).toEqual([])
  })

  it('uses the exact screen copy from the guidelines', () => {
    expect(en.home.headline).toBe('Spotted a pothole?')
    expect(en.home.subtext).toBe('Report it in 30 seconds. No sign-up needed.')
    expect(en.review.privacy).toBe("We blur faces and number plates. We don't collect your name or number.")
    expect(en.result.titleMerged).toBe('Thanks! Added to an existing report.')
    expect(en.drive.safety).toBe("Mount your phone before you ride. Don't touch it while moving.")
    expect(en.admin.demo).toBe('Try the demo account (read only)')
    expect(en.admin.fixFirst).toBe('Fix these first')
  })
})
