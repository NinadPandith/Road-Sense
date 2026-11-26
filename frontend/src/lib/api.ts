import { API_URL } from './config'

/** Error codes from the backend's shared error shape (docs/backend-schema.md). */
export type ErrorCode =
  | 'invalid_image'
  | 'image_too_dark'
  | 'outside_pilot_area'
  | 'rate_limited'
  | 'not_found'
  | 'forbidden_demo'
  | 'invalid_transition'
  | 'survey_gpx_mismatch'
  | 'unauthorized'
  | 'validation_error'
  | 'internal'
  | 'network'

export class ApiError extends Error {
  readonly code: ErrorCode
  readonly status: number
  readonly retryAfterS?: number

  constructor(code: ErrorCode, status: number, message: string, retryAfterS?: number) {
    super(message)
    this.code = code
    this.status = status
    this.retryAfterS = retryAfterS
  }
}

/** i18n key for each error code, so screens show Content Guidelines copy, not server text. */
export const ERROR_KEYS: Record<ErrorCode, string> = {
  invalid_image: 'errors.invalidImage',
  image_too_dark: 'errors.tooDark',
  outside_pilot_area: 'errors.outsidePilot',
  rate_limited: 'errors.rateLimited',
  not_found: 'errors.wrongCode',
  forbidden_demo: 'errors.demoReadOnly',
  invalid_transition: 'errors.invalidTransition',
  survey_gpx_mismatch: 'errors.generic',
  unauthorized: 'errors.sessionExpired',
  validation_error: 'errors.generic',
  internal: 'errors.generic',
  network: 'errors.uploadFailed',
}

let tokenProvider: () => Promise<string | null> = async () => null

export function setTokenProvider(fn: () => Promise<string | null>) {
  tokenProvider = fn
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>

export function buildQuery(q?: Query): string {
  if (!q) return ''
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((item) => params.append(k, item))
    else params.append(k, String(v))
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

interface RequestOptions {
  method?: string
  query?: Query
  json?: unknown
  form?: FormData
  auth?: boolean
  signal?: AbortSignal
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {}
  if (opts.auth) {
    const token = await tokenProvider()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  let body: BodyInit | undefined
  if (opts.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.json)
  } else if (opts.form) {
    body = opts.form
  }
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}${buildQuery(opts.query)}`, {
      method: opts.method ?? (body ? 'POST' : 'GET'),
      headers,
      body,
      signal: opts.signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError('network', 0, 'Network error')
  }
  if (!res.ok) {
    let code: ErrorCode = 'internal'
    let message = res.statusText
    let retry: number | undefined
    try {
      const data = await res.json()
      code = data?.error?.code ?? code
      message = data?.error?.message ?? message
      retry = data?.error?.retry_after_s
    } catch {
      /* not JSON */
    }
    throw new ApiError(code, res.status, message, retry)
  }
  return res
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(path, opts)
  return (await res.json()) as T
}

export async function apiBlob(path: string, opts: RequestOptions = {}): Promise<Blob> {
  return (await send(path, opts)).blob()
}

/** POST a form with upload progress (fetch can't report it), same error shape as api(). */
export async function apiUpload<T>(path: string, form: FormData, onProgress: (f: number) => void): Promise<T> {
  const token = await tokenProvider()
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}${path}`)
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total)
    xhr.onerror = () => reject(new ApiError('network', 0, 'Network error'))
    xhr.onload = () => {
      let data: unknown = null
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        /* not JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(data as T)
      const err = (data as { error?: { code?: ErrorCode; message?: string } } | null)?.error
      reject(new ApiError(err?.code ?? 'internal', xhr.status, err?.message ?? xhr.statusText))
    }
    xhr.send(form)
  })
}
