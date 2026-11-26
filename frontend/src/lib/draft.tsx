import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Fix } from './location'

/** The report being made, carried from Capture (P2) to Review (P3). */
export interface Draft {
  photo: Blob
  previewUrl: string
  capturedAt: Date
  fix: Fix | null
  locationError: boolean
}

interface DraftState {
  draft: Draft | null
  setDraft: (d: Draft | null) => void
}

const DraftContext = createContext<DraftState | null>(null)

export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraftState] = useState<Draft | null>(null)
  const value = useMemo(
    () => ({
      draft,
      setDraft(d: Draft | null) {
        setDraftState((old) => {
          if (old && old.previewUrl !== d?.previewUrl) URL.revokeObjectURL(old.previewUrl)
          return d
        })
      },
    }),
    [draft],
  )
  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDraft(): DraftState {
  const ctx = useContext(DraftContext)
  if (!ctx) throw new Error('useDraft outside DraftProvider')
  return ctx
}
