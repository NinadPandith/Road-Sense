// Drive mode: run YOLO nano in the browser with ONNX Runtime Web (WebGPU, WASM fallback).
import type { InferenceSession } from 'onnxruntime-web'
import { letterboxParams, postprocess, toTensor, type Det } from './yolo'

export const MODEL_URL = '/models/yolo-nano.onnx'
const INPUT = 640

export class BrowserDetector {
  private canvas: HTMLCanvasElement | OffscreenCanvas
  private ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D

  private constructor(
    private session: InferenceSession,
    private ort: typeof import('onnxruntime-web'),
    readonly backend: string,
  ) {
    this.canvas =
      typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(INPUT, INPUT) : document.createElement('canvas')
    this.canvas.width = INPUT
    this.canvas.height = INPUT
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true }) as CanvasRenderingContext2D
  }

  static async load(onProgress?: (fraction: number) => void): Promise<BrowserDetector> {
    const ort = await import('onnxruntime-web')
    ort.env.wasm.wasmPaths = '/ort/'
    const model = await fetchWithProgress(MODEL_URL, onProgress)
    const hasWebGpu = typeof navigator !== 'undefined' && 'gpu' in navigator
    for (const ep of hasWebGpu ? ['webgpu', 'wasm'] : ['wasm']) {
      try {
        const session = await ort.InferenceSession.create(model, { executionProviders: [ep] })
        return new BrowserDetector(session, ort, ep)
      } catch {
        /* try the next backend */
      }
    }
    throw new Error('no ONNX backend available')
  }

  async detect(source: CanvasImageSource, w: number, h: number, conf = 0.35): Promise<Det[]> {
    const lb = letterboxParams(w, h, INPUT)
    const ctx = this.ctx
    ctx.fillStyle = 'rgb(114,114,114)'
    ctx.fillRect(0, 0, INPUT, INPUT)
    ctx.drawImage(source, lb.padX, lb.padY, Math.round(w * lb.scale), Math.round(h * lb.scale))
    const pixels = ctx.getImageData(0, 0, INPUT, INPUT).data
    const input = new this.ort.Tensor('float32', toTensor(pixels, INPUT), [1, 3, INPUT, INPUT])
    const out = await this.session.run({ [this.session.inputNames[0]]: input })
    const tensor = out[this.session.outputNames[0]]
    return postprocess(tensor.data as Float32Array, tensor.dims, lb, w, h, conf)
  }
}

async function fetchWithProgress(url: string, onProgress?: (f: number) => void): Promise<ArrayBuffer> {
  const res = await fetch(url)
  if (!res.ok || !res.body) throw new Error(`model download failed: ${res.status}`)
  const total = Number(res.headers.get('content-length')) || 0
  const reader = res.body.getReader()
  const chunks: Uint8Array[] = []
  let got = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    got += value.length
    if (total) onProgress?.(got / total)
  }
  const buf = new Uint8Array(got)
  let off = 0
  for (const c of chunks) {
    buf.set(c, off)
    off += c.length
  }
  return buf.buffer
}
