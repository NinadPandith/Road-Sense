// Offline outbox (F7): reports wait in IndexedDB and are sent when the phone is back online.
// Each item keeps its client_report_id, so a retry never creates a second report.
import { ApiError } from './api'
import { newId as makeId, submitReport } from './reports'

export interface OutboxItem {
  id: string
  photo: Blob
  lat: number
  lon: number
  accuracy: number | null
  capturedAt: string
  note: string
  source: 'citizen' | 'drive'
  createdAt: string
  attempts: number
}

/** What is stored: the photo as bytes, since Blobs don't survive IndexedDB everywhere. */
interface StoredItem extends Omit<OutboxItem, 'photo'> {
  photoBytes: ArrayBuffer
  photoType: string
}

const DB = 'roadsense'
const STORE = 'outbox'

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1)
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' })
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open()
  return new Promise<T>((resolve, reject) => {
    const t = db.transaction(STORE, mode)
    const req = fn(t.objectStore(STORE))
    t.oncomplete = () => {
      db.close()
      resolve(req.result)
    }
    t.onerror = () => {
      db.close()
      reject(t.error)
    }
  })
}

const listeners = new Set<() => void>()
export function onOutboxChange(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
const notify = () => listeners.forEach((fn) => fn())

export const newId = makeId

export async function enqueue(item: Omit<OutboxItem, 'createdAt' | 'attempts'>): Promise<void> {
  const { photo, ...rest } = item
  const stored: StoredItem = {
    ...rest,
    photoBytes: await photo.arrayBuffer(),
    photoType: photo.type || 'image/jpeg',
    createdAt: new Date().toISOString(),
    attempts: 0,
  }
  await tx('readwrite', (s) => s.put(stored))
  notify()
}

export async function pending(): Promise<OutboxItem[]> {
  const rows = await tx('readonly', (s) => s.getAll() as IDBRequest<StoredItem[]>)
  return rows.map(({ photoBytes, photoType, ...rest }) => ({
    ...rest,
    photo: new Blob([photoBytes], { type: photoType }),
  }))
}

async function remove(id: string): Promise<void> {
  await tx('readwrite', (s) => s.delete(id))
}

let flushing: Promise<number> | null = null

/** Send everything waiting. Stops at the first network error; drops items the server refuses. */
export function flush(): Promise<number> {
  flushing ??= (async () => {
    let sent = 0
    try {
      for (const item of await pending()) {
        try {
          await submitReport({
            photo: item.photo,
            lat: item.lat,
            lon: item.lon,
            accuracy: item.accuracy,
            capturedAt: new Date(item.capturedAt),
            note: item.note,
            source: item.source,
            clientReportId: item.id,
          })
          await remove(item.id)
          sent++
        } catch (e) {
          if (!(e instanceof ApiError) || e.code === 'network' || e.code === 'rate_limited' || e.status >= 500) {
            break // try again later
          }
          await remove(item.id) // refused for good (outside the pilot area, not a photo...)
        }
      }
    } finally {
      flushing = null
      notify()
    }
    return sent
  })()
  return flushing
}

/** Flush on start-up and whenever the phone comes back online. */
export function startOutbox(): void {
  window.addEventListener('online', () => void flush())
  if (navigator.onLine) void flush()
}
