import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert } from '../../components/Alert'
import { CameraIcon } from '../../components/Icons'
import { useDraft } from '../../lib/draft'
import { capturedAtFromExif, fixFromExif, getCurrentFix, type Fix } from '../../lib/location'

/** P2 Capture: take a photo or pick one; GPS from the browser, or from EXIF for gallery photos. */
export function CapturePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { setDraft } = useDraft()
  const cameraInput = useRef<HTMLInputElement>(null)
  const galleryInput = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [cameraError, setCameraError] = useState(false)
  const fixPromise = useRef<Promise<Fix | null> | null>(null)

  // Start asking for location as soon as the user chooses to take a photo, so the fix is
  // ready by the time the photo is.
  function startLocation() {
    fixPromise.current ??= getCurrentFix().catch(() => null)
  }

  async function onFile(file: File | undefined, fromGallery: boolean) {
    if (!file) return
    setBusy(true)
    let fix: Fix | null = fromGallery ? await fixFromExif(file) : null
    if (!fix) {
      startLocation()
      fix = await fixPromise.current
    }
    const capturedAt = (fromGallery && (await capturedAtFromExif(file))) || new Date()
    setDraft({
      photo: file,
      previewUrl: URL.createObjectURL(file),
      capturedAt,
      fix,
      locationError: !fix,
    })
    navigate('/report/review')
  }

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t('capture.title')}</h1>
      <p className="text-lg">{t('capture.instruction')}</p>
      <p className="text-slate-700">{t('permission.explain')}</p>
      {cameraError && (
        <Alert
          tone="error"
          action={
            <button type="button" className="btn btn-secondary" onClick={() => galleryInput.current?.click()}>
              {t('buttons.chooseGallery')}
            </button>
          }
        >
          {t('errors.cameraBlocked')}
        </Alert>
      )}
      {busy && <Alert>{t('capture.gettingLocation')}</Alert>}
      <input
        ref={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => void onFile(e.target.files?.[0], false)}
      />
      <input
        ref={galleryInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => void onFile(e.target.files?.[0], true)}
      />
      <button
        type="button"
        className="btn btn-primary min-h-16 text-lg"
        disabled={busy}
        onClick={() => {
          startLocation()
          try {
            cameraInput.current?.click()
          } catch {
            setCameraError(true)
          }
        }}
      >
        <CameraIcon />
        {t('capture.takePhoto')}
      </button>
      <button
        type="button"
        className="btn btn-secondary min-h-14"
        disabled={busy}
        onClick={() => galleryInput.current?.click()}
      >
        {t('capture.chooseGallery')}
      </button>
    </section>
  )
}
