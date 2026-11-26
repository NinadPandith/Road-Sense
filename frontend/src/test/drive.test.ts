import 'fake-indexeddb/auto'
import { EventKeeper, Odometer, type Capture } from '../lib/drive'
import { letterboxParams, postprocess } from '../lib/yolo'

function raw(rows: [number, number, number, number, number, number][], nc = 4) {
  const n = rows.length
  const out = new Float32Array((4 + nc) * n)
  rows.forEach(([cx, cy, w, h, c, s], i) => {
    out[i] = cx
    out[n + i] = cy
    out[2 * n + i] = w
    out[3 * n + i] = h
    out[(4 + c) * n + i] = s
  })
  return { out, dims: [1, 4 + nc, n] }
}

describe('yolo postprocess (same maths as the backend)', () => {
  it('maps boxes back through the letterbox', () => {
    const lb = letterboxParams(1280, 720, 640)
    expect(lb).toMatchObject({ scale: 0.5, padX: 0, padY: 140 })
    const { out, dims } = raw([[320, 320, 64, 32, 3, 0.9]])
    const [d] = postprocess(out, dims, lb, 1280, 720, 0.35)
    expect(d.damageClass).toBe('pothole')
    expect((d.box[0] + d.box[2]) / 2).toBeCloseTo(0.5, 3)
    expect((d.box[1] + d.box[3]) / 2).toBeCloseTo(0.5, 3)
  })

  it('drops weak boxes and same-class overlaps', () => {
    const lb = letterboxParams(640, 640, 640)
    const { out, dims } = raw([
      [100, 100, 50, 50, 3, 0.9],
      [102, 101, 50, 50, 3, 0.8],
      [102, 101, 50, 50, 0, 0.7],
      [400, 400, 50, 50, 1, 0.2],
    ])
    const dets = postprocess(out, dims, lb, 640, 640, 0.35)
    expect(dets.map((d) => [d.damageClass, d.confidence])).toEqual([
      ['pothole', expect.closeTo(0.9, 5)],
      ['crack_along', expect.closeTo(0.7, 5)],
    ])
  })
})

const fix = { lat: 12.97, lon: 77.59, accuracy: 5, t: 0 }
const cap = (t: number, confidence: number): Capture => ({ t, fix, dets: [], confidence, frame: null })

describe('EventKeeper (one frame per defect within 2 s)', () => {
  it('keeps the most confident frame of a run and emits it after a 2 s gap', () => {
    const k = new EventKeeper()
    expect(k.offer(cap(0, 0.6), 0)).toBeNull()
    expect(k.offer(cap(200, 0.9), 200)).toBeNull()
    expect(k.offer(cap(400, 0.7), 400)).toBeNull()
    expect(k.offer(null, 1500)).toBeNull()
    const done = k.offer(null, 2600)
    expect(done?.confidence).toBe(0.9)
    expect(k.flush()).toBeNull()
  })

  it('starts a new run after the gap', () => {
    const k = new EventKeeper()
    k.offer(cap(0, 0.6), 0)
    const first = k.offer(cap(3000, 0.8), 3000)
    expect(first?.confidence).toBe(0.6)
    expect(k.flush()?.confidence).toBe(0.8)
  })
})

describe('Odometer', () => {
  it('adds up distance and ignores poor fixes and jumps', () => {
    const o = new Odometer()
    o.add({ lat: 12.97, lon: 77.59, accuracy: 5, t: 0 })
    o.add({ lat: 12.97 + 100 / 111_320, lon: 77.59, accuracy: 5, t: 10_000 })
    expect(o.metres).toBeCloseTo(100, 0)
    o.add({ lat: 13.5, lon: 77.59, accuracy: 5, t: 11_000 }) // GPS jump
    o.add({ lat: 12.98, lon: 77.59, accuracy: 80, t: 12_000 }) // poor fix
    expect(o.metres).toBeCloseTo(100, 0)
  })
})

describe('outbox', () => {
  it('keeps reports while offline and sends them later with the same id', async () => {
    const { enqueue, flush, pending } = await import('../lib/outbox')
    const calls: FormData[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        if (calls.length === 0) {
          calls.push(init.body as FormData)
          throw new TypeError('offline')
        }
        calls.push(init.body as FormData)
        return new Response(JSON.stringify({ tracking_code: 'RS-7K2Q', thumb_url: null }), { status: 200 })
      }),
    )
    await enqueue({
      id: 'abc', photo: new Blob(['x'], { type: 'image/jpeg' }), lat: 1, lon: 2, accuracy: null,
      capturedAt: new Date().toISOString(), note: '', source: 'citizen',
    })
    expect(await flush()).toBe(0)
    expect((await pending()).length).toBe(1)
    expect(await flush()).toBe(1)
    expect((await pending()).length).toBe(0)
    expect(calls[1].get('client_report_id')).toBe('abc')
    vi.unstubAllGlobals()
  })
})
