// Drive mode logic that doesn't touch the camera: de-duplication and distance.
import type { Det } from './yolo'

export const UPLOAD_CONFIDENCE = 0.5 // App Flow: a detection above 0.5 saves the frame
export const SAME_DEFECT_MS = 2000 // same defect in consecutive frames within 2 s -> saved once
export const SLOW_FPS = 2 // below this, fall back to sending a photo every 2 s

export interface Fix {
  lat: number
  lon: number
  accuracy: number
  t: number
}

export interface Capture {
  t: number
  fix: Fix
  dets: Det[]
  confidence: number
  frame: Blob | null
}

/** Keeps the highest-confidence frame of a run of detections; emits it once the run ends. */
export class EventKeeper {
  private current: Capture | null = null
  private lastSeen = 0

  /** Feed a frame result. Returns a finished capture to save, if one just ended. */
  offer(c: Capture | null, now: number): Capture | null {
    let finished: Capture | null = null
    if (this.current && now - this.lastSeen > SAME_DEFECT_MS) {
      finished = this.current
      this.current = null
    }
    if (c) {
      if (!this.current || c.confidence > this.current.confidence) this.current = c
      this.lastSeen = now
    }
    return finished
  }

  /** At Stop: the last open run. */
  flush(): Capture | null {
    const c = this.current
    this.current = null
    return c
  }

  /** True when the next detection with this confidence would replace the stored frame. */
  wouldKeep(confidence: number, now: number): boolean {
    return !this.current || now - this.lastSeen > SAME_DEFECT_MS || confidence > this.current.confidence
  }
}

export function haversineM(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const R = 6_371_000
  const rad = Math.PI / 180
  const dp = (b.lat - a.lat) * rad
  const dl = (b.lon - a.lon) * rad
  const h = Math.sin(dp / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dl / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

/** Adds up distance from GPS fixes, ignoring poor fixes and GPS jumps. */
export class Odometer {
  metres = 0
  private last: Fix | null = null

  add(f: Fix): void {
    if (f.accuracy > 30) return
    if (this.last) {
      const d = haversineM(this.last, f)
      const dt = (f.t - this.last.t) / 1000
      if (dt > 0 && d / dt < 45) this.metres += d // ignore jumps faster than ~160 km/h
    }
    this.last = f
  }
}
