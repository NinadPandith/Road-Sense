// Small inline icons. Decorative unless given a title.
import type { SeverityLabel } from '../lib/types'

type P = { className?: string }

export function SeverityIcon({ label, className = 'h-4 w-4' }: { label: SeverityLabel } & P) {
  if (label === 'minor')
    return (
      <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
        <circle cx="8" cy="8" r="6" fill="currentColor" />
      </svg>
    )
  if (label === 'moderate')
    return (
      <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
        <path d="M8 1.5 15 14H1z" fill="currentColor" />
      </svg>
    )
  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      <path d="M8 .8 15.2 8 8 15.2.8 8z" fill="currentColor" />
      <path d="M8 4.2v4.6M8 10.8v1" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function CameraIcon({ className = 'h-6 w-6' }: P) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" strokeLinejoin="round" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  )
}

export function SearchIcon({ className = 'h-6 w-6' }: P) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" strokeLinecap="round" />
    </svg>
  )
}

export function CarIcon({ className = 'h-6 w-6' }: P) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 16V12l2-5h12l2 5v4z" strokeLinejoin="round" />
      <circle cx="7.5" cy="16.5" r="1.8" />
      <circle cx="16.5" cy="16.5" r="1.8" />
    </svg>
  )
}

export function MapIcon({ className = 'h-6 w-6' }: P) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z" strokeLinejoin="round" />
      <path d="M9 4v14M15 6v14" />
    </svg>
  )
}

export function HomeIcon({ className = 'h-6 w-6' }: P) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 11 12 4l8 7v9h-5v-6H9v6H4z" strokeLinejoin="round" />
    </svg>
  )
}
