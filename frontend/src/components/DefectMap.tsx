import { useEffect } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { MAP_CENTER } from '../lib/config'
import { SEVERITY_COLOURS } from './Badges'
import { OSM_ATTRIBUTION, OSM_TILES } from './PinMap'
import type { ReactNode } from 'react'
import type { SeverityLabel } from '../lib/types'

export interface MapPoint {
  id: string
  lat: number
  lon: number
  severity: SeverityLabel | null
  fixed?: boolean
  popup?: ReactNode
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    map.fitBounds(
      points.map((p) => [p.lat, p.lon] as [number, number]),
      { padding: [30, 30], maxZoom: 17 },
    )
    // Fit only when the set of points changes in size, not on every refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points.length, map])
  return null
}

/** Severity-coloured markers (green / amber / red). Size grows with severity so colour isn't
 * the only cue; popups carry the word. */
export function DefectMap({
  points,
  className = 'h-96',
  label,
  children,
}: {
  points: MapPoint[]
  className?: string
  label: string
  children?: ReactNode
}) {
  return (
    <div className={`${className} overflow-hidden rounded-2xl border border-slate-200`} role="region" aria-label={label}>
      <MapContainer center={MAP_CENTER} zoom={13} className="h-full w-full">
        <TileLayer url={OSM_TILES} attribution={OSM_ATTRIBUTION} maxZoom={19} />
        {points.map((p) => {
          const colour = p.fixed ? SEVERITY_COLOURS.fixed : SEVERITY_COLOURS[p.severity ?? 'none']
          const radius = p.severity === 'dangerous' ? 10 : p.severity === 'moderate' ? 8 : 6
          return (
            <CircleMarker
              key={p.id}
              center={[p.lat, p.lon]}
              radius={radius}
              pathOptions={{ color: '#fff', weight: 2, fillColor: colour, fillOpacity: 0.9 }}
            >
              {p.popup && <Popup>{p.popup}</Popup>}
            </CircleMarker>
          )
        })}
        <FitBounds points={points} />
        {children}
      </MapContainer>
    </div>
  )
}
