// YOLO ONNX output decoding in the browser: a port of backend/app/services/detect.py, so Drive
// mode and the server read the model the same way.
import type { DamageClass } from './types'

/** Model class index -> damage type, RDD2022 order (D00, D10, D20, D40). */
export const INDEX_TO_CLASS: DamageClass[] = ['crack_along', 'crack_across', 'alligator_crack', 'pothole']

export interface Det {
  damageClass: DamageClass
  confidence: number
  /** x1, y1, x2, y2 as fractions of the frame */
  box: [number, number, number, number]
}

export interface Letterbox {
  scale: number
  padX: number
  padY: number
  size: number
}

export function letterboxParams(w: number, h: number, size = 640): Letterbox {
  const scale = Math.min(size / w, size / h)
  const nw = Math.round(w * scale)
  const nh = Math.round(h * scale)
  return { scale, padX: Math.floor((size - nw) / 2), padY: Math.floor((size - nh) / 2), size }
}

/** RGBA pixels of the letterboxed square -> 1x3xSxS float tensor data (RGB, 0-1). */
export function toTensor(rgba: Uint8ClampedArray, size: number): Float32Array {
  const plane = size * size
  const out = new Float32Array(3 * plane)
  for (let i = 0; i < plane; i++) {
    out[i] = rgba[i * 4] / 255
    out[plane + i] = rgba[i * 4 + 1] / 255
    out[2 * plane + i] = rgba[i * 4 + 2] / 255
  }
  return out
}

function iou(a: number[], b: number[]): number {
  const x1 = Math.max(a[0], b[0])
  const y1 = Math.max(a[1], b[1])
  const x2 = Math.min(a[2], b[2])
  const y2 = Math.min(a[3], b[3])
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1)
  const area = (r: number[]) => (r[2] - r[0]) * (r[3] - r[1])
  return inter / (area(a) + area(b) - inter + 1e-9)
}

/** output: flat 1 x (4 + nc) x N array (Ultralytics layout). */
export function postprocess(
  output: Float32Array,
  dims: readonly number[],
  lb: Letterbox,
  frameW: number,
  frameH: number,
  confThreshold: number,
  iouThreshold = 0.5,
): Det[] {
  const rows = dims[1]
  const n = dims[2]
  const nc = rows - 4
  const cand: { cls: number; conf: number; box: number[] }[] = []
  for (let i = 0; i < n; i++) {
    let best = 0
    let cls = 0
    for (let c = 0; c < nc; c++) {
      const v = output[(4 + c) * n + i]
      if (v > best) {
        best = v
        cls = c
      }
    }
    if (best < confThreshold) continue
    const cx = output[i]
    const cy = output[n + i]
    const w = output[2 * n + i]
    const h = output[3 * n + i]
    const fx = (v: number) => Math.min(Math.max((v - lb.padX) / lb.scale, 0), frameW) / frameW
    const fy = (v: number) => Math.min(Math.max((v - lb.padY) / lb.scale, 0), frameH) / frameH
    cand.push({ cls, conf: best, box: [fx(cx - w / 2), fy(cy - h / 2), fx(cx + w / 2), fy(cy + h / 2)] })
  }
  cand.sort((a, b) => b.conf - a.conf)
  const kept: typeof cand = []
  for (const c of cand) {
    if (kept.every((k) => k.cls !== c.cls || iou(k.box, c.box) <= iouThreshold)) kept.push(c)
  }
  return kept.map((k) => ({
    damageClass: INDEX_TO_CLASS[k.cls],
    confidence: k.conf,
    box: k.box as [number, number, number, number],
  }))
}
