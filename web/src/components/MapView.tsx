'use client'

import { MapContainer, TileLayer, CircleMarker, Popup, Polygon, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

// ─── Types ───────────────────────────────────────────────────────────────────
interface Dealer {
  name:   string
  lat:    number
  lon:    number
  region: string
  active: boolean
}

interface Props {
  dealers:       Dealer[]
  regionColors:  Record<string, string>
  selectedDealer: Dealer | null
  onSelectDealer: (d: Dealer) => void
}

// ─── Turkey 7-Region Polygons (lat, lon pairs) ────────────────────────────────
const REGION_POLYGONS: Record<string, [number, number][]> = {
  'Marmara': [
    [41.9,26.0],[42.0,27.5],[41.8,28.5],[41.4,29.1],[41.2,30.5],
    [41.5,32.0],[40.5,32.0],[40.0,30.5],[39.5,28.0],[39.5,26.5],[40.0,26.2],
  ],
  'Karadeniz': [
    [41.5,32.0],[41.7,33.5],[41.5,35.0],[41.3,36.5],[41.1,38.0],
    [41.3,40.5],[41.5,41.5],[41.5,43.5],[40.3,44.5],
    [40.5,44.0],[40.5,40.5],[40.5,38.0],[40.5,32.0],
  ],
  'Ege': [
    [39.5,26.5],[39.5,28.0],[40.0,30.5],[37.5,30.5],
    [36.4,30.5],[36.2,29.0],[36.5,28.0],[36.8,27.5],
    [37.0,27.2],[37.5,27.0],[38.3,26.5],[39.0,26.3],
  ],
  'İç Anadolu': [
    [40.5,32.0],[40.5,38.0],[37.5,38.0],[37.5,30.5],[40.0,30.5],
  ],
  'Akdeniz': [
    [37.5,30.5],[37.5,37.0],[36.7,37.0],[36.5,36.5],[36.4,36.0],
    [36.2,35.0],[36.0,34.0],[36.0,33.0],[36.2,31.5],[36.4,30.5],
  ],
  'Doğu Anadolu': [
    [40.5,38.0],[40.5,44.0],[40.3,44.5],[39.5,44.5],
    [38.5,44.5],[37.5,44.0],[37.5,38.0],
  ],
  'Güneydoğu Anadolu': [
    [37.5,37.0],[37.5,38.0],[37.5,44.0],[37.2,44.3],
    [37.0,43.5],[36.8,42.5],[36.8,41.5],[37.1,40.5],
    [36.7,38.5],[36.7,37.0],
  ],
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function MapView({ dealers, regionColors, selectedDealer, onSelectDealer }: Props) {
  return (
    <MapContainer
      center={[39.0, 35.5]}
      zoom={6}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Region polygons */}
      {Object.entries(REGION_POLYGONS).map(([region, positions]) => (
        <Polygon
          key={region}
          positions={positions}
          pathOptions={{
            color:       regionColors[region] ?? '#94a3b8',
            fillColor:   regionColors[region] ?? '#94a3b8',
            fillOpacity: 0.12,
            weight:      1.5,
          }}
        >
          <Tooltip sticky>{region}</Tooltip>
        </Polygon>
      ))}

      {/* Dealer markers */}
      {dealers.map(dealer => {
        const isSelected = selectedDealer?.name === dealer.name
        const color = regionColors[dealer.region] ?? '#94a3b8'
        return (
          <CircleMarker
            key={dealer.name}
            center={[dealer.lat, dealer.lon]}
            radius={isSelected ? 12 : dealer.active ? 8 : 6}
            pathOptions={{
              color:       isSelected ? '#1e40af' : color,
              fillColor:   dealer.active ? color : '#94a3b8',
              fillOpacity: dealer.active ? 0.85 : 0.4,
              weight:      isSelected ? 3 : 1.5,
            }}
            eventHandlers={{ click: () => onSelectDealer(dealer) }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{dealer.name}</p>
                <p className="text-slate-500 text-xs">{dealer.region}</p>
                <p className="text-slate-400 text-xs mt-1 font-mono">
                  {dealer.lat.toFixed(4)}, {dealer.lon.toFixed(4)}
                </p>
                <span className={`mt-1 inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                  dealer.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  {dealer.active ? 'Aktif' : 'Pasif'}
                </span>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
