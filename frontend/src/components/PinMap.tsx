import L from 'leaflet'
import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet'

export const OSM_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
export const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export const pinIcon = L.divIcon({
  className: '',
  html: '<svg width="34" height="44" viewBox="0 0 34 44" aria-hidden="true"><path d="M17 1C8 1 1 8 1 17c0 12 16 26 16 26s16-14 16-26C33 8 26 1 17 1z" fill="#0f766e" stroke="#fff" stroke-width="2"/><circle cx="17" cy="17" r="6" fill="#fff"/></svg>',
  iconSize: [34, 44],
  iconAnchor: [17, 43],
})

function Recenter({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView([lat, lon])
  }, [lat, lon, map])
  return null
}

/** Small map with a draggable pin (Review screen P3). */
export function PinMap({
  lat,
  lon,
  onMove,
  label,
}: {
  lat: number
  lon: number
  onMove: (lat: number, lon: number) => void
  label: string
}) {
  const markerRef = useRef<L.Marker>(null)
  const handlers = useMemo(
    () => ({
      dragend() {
        const p = markerRef.current?.getLatLng()
        if (p) onMove(p.lat, p.lng)
      },
    }),
    [onMove],
  )
  return (
    <div className="h-56 overflow-hidden rounded-xl border border-slate-200" role="group" aria-label={label}>
      <MapContainer center={[lat, lon]} zoom={18} className="h-full w-full" scrollWheelZoom={false}>
        <TileLayer url={OSM_TILES} attribution={OSM_ATTRIBUTION} maxZoom={19} />
        <Marker
          position={[lat, lon]}
          draggable
          eventHandlers={handlers}
          ref={markerRef}
          icon={pinIcon}
          keyboard
          title={label}
        />
        <Recenter lat={lat} lon={lon} />
      </MapContainer>
    </div>
  )
}
