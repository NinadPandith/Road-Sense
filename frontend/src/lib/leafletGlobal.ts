// Leaflet 1.x plugins (leaflet.heat, leaflet.markercluster) attach to a global `L`.
import L from 'leaflet'

declare global {
  interface Window {
    L: typeof L
  }
}

window.L = L
