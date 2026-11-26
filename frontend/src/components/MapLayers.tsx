import L from 'leaflet'
import '../lib/leafletGlobal'
import 'leaflet.heat'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import type { SeverityLabel } from '../lib/types'
import { SEVERITY_COLOURS } from './Badges'

export interface LayerPoint {
  id: string
  lat: number
  lon: number
  severity: SeverityLabel | null
  /** Plain-text popup lines; the last link opens the defect. */
  title: string
  subtitle: string
  linkText: string
  href: string
}

const WEIGHT: Record<SeverityLabel, number> = { minor: 0.35, moderate: 0.65, dangerous: 1 }

/** Severity-weighted heatmap (leaflet.heat). */
export function HeatLayer({ points }: { points: LayerPoint[] }) {
  const map = useMap()
  useEffect(() => {
    const layer = L.heatLayer(
      points.map((p) => [p.lat, p.lon, p.severity ? WEIGHT[p.severity] : 0.3]),
      { radius: 22, blur: 18, maxZoom: 17, minOpacity: 0.35 },
    )
    layer.addTo(map)
    return () => {
      layer.remove()
    }
  }, [map, points])
  return null
}

/** Markers that cluster when zoomed out. Popups are built from text nodes (no HTML injection);
 * the link is handled by the router via onOpen. */
export function ClusterLayer({ points, onOpen }: { points: LayerPoint[]; onOpen: (href: string) => void }) {
  const map = useMap()
  useEffect(() => {
    const group = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45 })
    for (const p of points) {
      const radius = p.severity === 'dangerous' ? 10 : p.severity === 'moderate' ? 8 : 6
      const m = L.circleMarker([p.lat, p.lon], {
        radius,
        color: '#fff',
        weight: 2,
        fillColor: SEVERITY_COLOURS[p.severity ?? 'none'],
        fillOpacity: 0.9,
      })
      const box = document.createElement('div')
      box.className = 'flex flex-col gap-1 text-sm'
      const title = document.createElement('strong')
      title.textContent = p.title
      const sub = document.createElement('span')
      sub.textContent = p.subtitle
      const link = document.createElement('a')
      link.href = p.href
      link.textContent = p.linkText
      link.addEventListener('click', (e) => {
        e.preventDefault()
        onOpen(p.href)
      })
      box.append(title, sub, link)
      m.bindPopup(box)
      group.addLayer(m as unknown as L.Marker)
    }
    map.addLayer(group)
    return () => {
      map.removeLayer(group)
    }
  }, [map, points, onOpen])
  return null
}
