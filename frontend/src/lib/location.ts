import exifr from 'exifr'

export interface Fix {
  lat: number
  lon: number
  accuracy: number | null
  source: 'gps' | 'exif' | 'manual'
}

export function getCurrentFix(timeoutMs = 15000): Promise<Fix> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('unsupported'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({
          lat: p.coords.latitude,
          lon: p.coords.longitude,
          accuracy: p.coords.accuracy,
          source: 'gps',
        }),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 10000 },
    )
  })
}

/** GPS from a gallery photo's EXIF, if the camera saved it. */
export async function fixFromExif(file: Blob): Promise<Fix | null> {
  try {
    const gps = await exifr.gps(file)
    if (gps && Number.isFinite(gps.latitude) && Number.isFinite(gps.longitude)) {
      return { lat: gps.latitude, lon: gps.longitude, accuracy: null, source: 'exif' }
    }
  } catch {
    /* no EXIF */
  }
  return null
}

export async function capturedAtFromExif(file: Blob): Promise<Date | null> {
  try {
    const data = await exifr.parse(file, ['DateTimeOriginal'])
    const d = data?.DateTimeOriginal
    return d instanceof Date && !Number.isNaN(d.getTime()) ? d : null
  } catch {
    return null
  }
}
