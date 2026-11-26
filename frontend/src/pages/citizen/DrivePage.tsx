import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import { Link } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { OSM_ATTRIBUTION, OSM_TILES } from '../../components/PinMap'
import type { BrowserDetector } from '../../lib/detector'
import { EventKeeper, Odometer, SLOW_FPS, UPLOAD_CONFIDENCE, type Capture, type Fix } from '../../lib/drive'
import { formatDistance } from '../../lib/format'
import { enqueue, flush, newId, onOutboxChange, pending } from '../../lib/outbox'
import type { Det } from '../../lib/yolo'

type Phase = 'safety' | 'session'
const SAFETY_KEY = 'roadsense.driveSafetySeen'
const TARGET_FPS = 5
const FALLBACK_EVERY_MS = 2000

const BOX_COLOURS: Record<Det['damageClass'], string> = {
  pothole: '#dc2626',
  alligator_crack: '#d97706',
  crack_across: '#16a34a',
  crack_along: '#16a34a',
}

function seenSafety(): boolean {
  try {
    return localStorage.getItem(SAFETY_KEY) === '1'
  } catch {
    return false
  }
}

/** P6 Drive mode: live detection in the browser, GPS, wake lock, background upload. */
export default function DrivePage() {
  const { t } = useTranslation()
  const [phase, setPhase] = useState<Phase>(seenSafety() ? 'session' : 'safety')

  if (phase === 'safety') {
    return (
      <section className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold">{t('drive.title')}</h1>
        <Alert tone="warning">{t('drive.safety')}</Alert>
        <button
          type="button"
          className="btn btn-primary min-h-14"
          onClick={() => {
            try {
              localStorage.setItem(SAFETY_KEY, '1')
            } catch {
              /* ignore */
            }
            setPhase('session')
          }}
        >
          {t('drive.understand')}
        </button>
      </section>
    )
  }
  return <DriveSession />
}

interface Stats {
  found: number
  queued: number
  sent: number
  metres: number
}

function DriveSession() {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const detectorRef = useRef<BrowserDetector | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const fixRef = useRef<Fix | null>(null)
  const routeRef = useRef<[number, number][]>([])
  const pointsRef = useRef<[number, number][]>([])
  const keeper = useRef(new EventKeeper())
  const odo = useRef(new Odometer())
  const running = useRef(false)
  const wakeLock = useRef<WakeLockSentinel | null>(null)
  const watchId = useRef<number | null>(null)

  const [state, setState] = useState<'loading' | 'ready' | 'running' | 'stopped'>('loading')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<'camera' | 'gps' | 'model' | null>(null)
  const [slow, setSlow] = useState<'no' | 'ask' | 'fallback'>('no')
  const [stats, setStats] = useState<Stats>({ found: 0, queued: 0, sent: 0, metres: 0 })
  const fpsRef = useRef(0)
  const [fps, setFps] = useState(0)
  const [waiting, setWaiting] = useState(0)
  const [summary, setSummary] = useState<{ route: [number, number][]; points: [number, number][] }>({ route: [], points: [] })

  // Count what has been sent: everything queued minus what is still waiting.
  useEffect(
    () =>
      onOutboxChange(() => {
        void pending().then((items) => {
          const left = items.filter((i) => i.source === 'drive').length
          setWaiting(left)
          setStats((s) => ({ ...s, sent: Math.max(0, s.queued - left) }))
        })
      }),
    [],
  )

  // Setup: GPS first (Drive mode won't start without it), then the model, then the camera.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await new Promise<void>((resolve, reject) =>
          navigator.geolocation.getCurrentPosition(() => resolve(), reject, { enableHighAccuracy: true, timeout: 20000 }),
        )
      } catch {
        if (!cancelled) setError('gps')
        return
      }
      try {
        const { BrowserDetector } = await import('../../lib/detector')
        detectorRef.current = await BrowserDetector.load((f) => !cancelled && setProgress(f))
      } catch {
        if (!cancelled) setError('model')
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        })
        if (cancelled) {
          stream.getTracks().forEach((tr) => tr.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        setState('ready')
      } catch {
        if (!cancelled) setError('camera')
      }
    })()
    return () => {
      cancelled = true
      running.current = false
      streamRef.current?.getTracks().forEach((tr) => tr.stop())
      if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current)
      void wakeLock.current?.release()
    }
  }, [])

  const save = useCallback(async (c: Capture) => {
    if (!c.frame) return
    pointsRef.current.push([c.fix.lat, c.fix.lon])
    await enqueue({
      id: newId(),
      photo: c.frame,
      lat: c.fix.lat,
      lon: c.fix.lon,
      accuracy: c.fix.accuracy,
      capturedAt: new Date(c.t).toISOString(),
      note: '',
      source: 'drive',
    })
    setStats((s) => ({ ...s, queued: s.queued + 1 }))
    void flush()
  }, [])

  const grabFrame = useCallback((): Promise<Blob | null> => {
    const v = videoRef.current
    if (!v || !v.videoWidth) return Promise.resolve(null)
    const c = document.createElement('canvas')
    c.width = v.videoWidth
    c.height = v.videoHeight
    c.getContext('2d')?.drawImage(v, 0, 0)
    return new Promise((resolve) => c.toBlob(resolve, 'image/jpeg', 0.85))
  }, [])

  const drawBoxes = useCallback((dets: Det[]) => {
    const canvas = overlayRef.current
    const v = videoRef.current
    if (!canvas || !v) return
    canvas.width = canvas.clientWidth
    canvas.height = canvas.clientHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.lineWidth = 3
    ctx.font = '14px system-ui'
    for (const d of dets) {
      const [x1, y1, x2, y2] = d.box
      ctx.strokeStyle = ctx.fillStyle = BOX_COLOURS[d.damageClass]
      ctx.strokeRect(x1 * canvas.width, y1 * canvas.height, (x2 - x1) * canvas.width, (y2 - y1) * canvas.height)
      ctx.fillText(`${t(`damage.${d.damageClass}`)} ${Math.round(d.confidence * 100)}%`, x1 * canvas.width + 4, y1 * canvas.height - 4)
    }
  }, [t])

  const slowModeRef = useRef<'no' | 'ask' | 'fallback'>('no')

  const loop = useCallback(async () => {
    const det = detectorRef.current
    const v = videoRef.current
    const times: number[] = []
    let lastFallback = 0
    while (running.current && det && v) {
      const started = performance.now()
      const fix = fixRef.current

      if (slowModeRef.current === 'fallback') {
        // Too slow for live detection: send a photo every 2 s and let the server check it.
        if (fix && Date.now() - lastFallback >= FALLBACK_EVERY_MS) {
          lastFallback = Date.now()
          await save({ t: Date.now(), fix, dets: [], confidence: 0, frame: await grabFrame() })
        }
        await new Promise((r) => setTimeout(r, 250))
        continue
      }

      let dets: Det[] = []
      try {
        dets = await det.detect(v, v.videoWidth, v.videoHeight, 0.35)
      } catch {
        dets = []
      }
      drawBoxes(dets)

      // Keep one frame per defect: the most confident one within 2 s (App Flow, Flow 3).
      const strong = dets.filter((d) => d.confidence >= UPLOAD_CONFIDENCE)
      const now = Date.now()
      let capture: Capture | null = null
      if (strong.length && fix) {
        const conf = Math.max(...strong.map((d) => d.confidence))
        if (keeper.current.wouldKeep(conf, now)) {
          capture = { t: now, fix, dets: strong, confidence: conf, frame: await grabFrame() }
        }
      }
      const finished = keeper.current.offer(capture, now)
      if (finished) {
        setStats((s) => ({ ...s, found: s.found + 1 }))
        await save(finished)
      }

      // Speed check after a short warm-up; the average is shown on the summary (experiment E6).
      times.push(performance.now() - started)
      if (times.length > 5) {
        const recent = times.slice(-30)
        fpsRef.current = 1000 / (recent.reduce((x, y) => x + y, 0) / recent.length)
      }
      if (times.length === 15 && slowModeRef.current === 'no') {
        const fps = 1000 / (times.slice(5).reduce((x, y) => x + y, 0) / 10)
        if (fps < SLOW_FPS) {
          slowModeRef.current = 'ask'
          setSlow('ask')
        }
      }
      const wait = 1000 / TARGET_FPS - (performance.now() - started)
      if (wait > 0) await new Promise((r) => setTimeout(r, wait))
    }
  }, [drawBoxes, grabFrame, save])

  async function start() {
    running.current = true
    setState('running')
    try {
      wakeLock.current = (await navigator.wakeLock?.request('screen')) ?? null
    } catch {
      /* not supported: the rider keeps the screen on manually */
    }
    watchId.current = navigator.geolocation.watchPosition(
      (p) => {
        const f = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, t: p.timestamp }
        fixRef.current = f
        odo.current.add(f)
        const last = routeRef.current.at(-1)
        if (!last || Math.abs(last[0] - f.lat) + Math.abs(last[1] - f.lon) > 0.00004) routeRef.current.push([f.lat, f.lon])
        setStats((s) => ({ ...s, metres: odo.current.metres }))
      },
      () => setError('gps'),
      { enableHighAccuracy: true, maximumAge: 1000 },
    )
    void loop()
  }

  async function stop() {
    running.current = false
    const last = keeper.current.flush()
    if (last) {
      setStats((s) => ({ ...s, found: s.found + 1 }))
      await save(last)
    }
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current)
    streamRef.current?.getTracks().forEach((tr) => tr.stop())
    await wakeLock.current?.release().catch(() => undefined)
    setSummary({ route: [...routeRef.current], points: [...pointsRef.current] })
    setFps(Math.min(fpsRef.current, TARGET_FPS * 10))
    setState('stopped')
  }

  const counter = t('drive.counter', { found: stats.found, sent: stats.sent, distance: formatDistance(stats.metres) })

  if (state === 'stopped') {
    const { route, points } = summary
    return (
      <section className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold">{t('drive.title')}</h1>
        <p className="text-lg" aria-live="polite">
          {t('drive.summary', { found: stats.found, distance: formatDistance(stats.metres) })}
        </p>
        <p className="text-slate-700">{counter}</p>
        {fps > 0 && <p className="text-sm text-slate-600">{t('drive.speed', { fps: fps.toFixed(1) })}</p>}
        {route.length > 0 && (
          <div className="h-64 overflow-hidden rounded-xl border border-slate-200">
            <MapContainer bounds={route} className="h-full w-full">
              <TileLayer url={OSM_TILES} attribution={OSM_ATTRIBUTION} />
              <Polyline positions={route} pathOptions={{ color: '#0f766e', weight: 4 }} />
              {points.map((p, i) => (
                <CircleMarker key={i} center={p} radius={6} pathOptions={{ color: '#fff', fillColor: '#dc2626', fillOpacity: 1 }} />
              ))}
            </MapContainer>
          </div>
        )}
        {waiting > 0 && (
          <button type="button" className="btn btn-primary" onClick={() => void flush()}>
            {t('drive.uploadRemaining', { count: waiting })}
          </button>
        )}
        <Link to="/" className="btn btn-secondary">
          {t('result.done')}
        </Link>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{t('drive.title')}</h1>
      {error === 'gps' && (
        <Alert tone="error" action={<button type="button" className="btn btn-secondary" onClick={() => window.location.reload()}>{t('buttons.openSettings')}</button>}>
          {t('errors.driveNoGps')}
        </Alert>
      )}
      {error === 'camera' && <Alert tone="error">{t('errors.cameraBlockedDrive')}</Alert>}
      {error === 'model' && <Alert tone="error">{t('errors.modelFailed')}</Alert>}
      {slow === 'ask' && (
        <Alert
          tone="warning"
          action={
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                slowModeRef.current = 'fallback'
                setSlow('fallback')
              }}
            >
              {t('buttons.continue')}
            </button>
          }
        >
          {t('errors.driveSlow')}
        </Alert>
      )}
      {!error && state === 'loading' && (
        <div aria-live="polite">
          <p>{t('drive.loadingModel', { percent: Math.round(progress * 100) })}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        </div>
      )}
      <div className="relative overflow-hidden rounded-2xl bg-black">
        <video ref={videoRef} playsInline muted className="aspect-video w-full object-cover" aria-label={t('drive.cameraLabel')} />
        <canvas ref={overlayRef} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true" />
        {state === 'running' && (
          <p className="absolute top-2 left-2 rounded-lg bg-black/70 px-3 py-1.5 text-lg font-semibold text-white tabular-nums" aria-live="off">
            {counter}
          </p>
        )}
      </div>
      {state === 'ready' && <p className="text-lg">{t('drive.setup')}</p>}
      {state === 'ready' && (
        <button type="button" className="btn btn-primary min-h-16 text-xl" onClick={() => void start()}>
          {t('drive.start')}
        </button>
      )}
      {state === 'running' && (
        <button type="button" className="btn btn-danger min-h-16 text-xl" onClick={() => void stop()}>
          {t('drive.stop')}
        </button>
      )}
    </section>
  )
}
