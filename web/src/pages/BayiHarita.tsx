import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polygon, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

interface Dealer { name: string; lat: number; lon: number; region: string; active: boolean }

const REGION_COLORS: Record<string, string> = {
  'Marmara':           '#3b82f6',
  'Karadeniz':         '#22c55e',
  'Ege':               '#f59e0b',
  'İç Anadolu':        '#8b5cf6',
  'Akdeniz':           '#ef4444',
  'Doğu Anadolu':      '#ec4899',
  'Güneydoğu Anadolu': '#14b8a6',
}

const REGION_POLYGONS: Record<string, [number,number][]> = {
  'Marmara':           [[41.9,26.0],[42.0,27.5],[41.8,28.5],[41.4,29.1],[41.2,30.5],[41.5,32.0],[40.5,32.0],[40.0,30.5],[39.5,28.0],[39.5,26.5],[40.0,26.2]],
  'Karadeniz':         [[41.5,32.0],[41.7,33.5],[41.5,35.0],[41.3,36.5],[41.1,38.0],[41.3,40.5],[41.5,41.5],[41.5,43.5],[40.3,44.5],[40.5,44.0],[40.5,40.5],[40.5,38.0],[40.5,32.0]],
  'Ege':               [[39.5,26.5],[39.5,28.0],[40.0,30.5],[37.5,30.5],[36.4,30.5],[36.2,29.0],[36.5,28.0],[36.8,27.5],[37.0,27.2],[37.5,27.0],[38.3,26.5],[39.0,26.3]],
  'İç Anadolu':        [[40.5,32.0],[40.5,38.0],[37.5,38.0],[37.5,30.5],[40.0,30.5]],
  'Akdeniz':           [[37.5,30.5],[37.5,37.0],[36.7,37.0],[36.5,36.5],[36.4,36.0],[36.2,35.0],[36.0,34.0],[36.0,33.0],[36.2,31.5],[36.4,30.5]],
  'Doğu Anadolu':      [[40.5,38.0],[40.5,44.0],[40.3,44.5],[39.5,44.5],[38.5,44.5],[37.5,44.0],[37.5,38.0]],
  'Güneydoğu Anadolu': [[37.5,37.0],[37.5,38.0],[37.5,44.0],[37.2,44.3],[37.0,43.5],[36.8,42.5],[36.8,41.5],[37.1,40.5],[36.7,38.5],[36.7,37.0]],
}

const REGIONS = Object.keys(REGION_COLORS)

export default function BayiHarita() {
  const [dealers, setDealers]       = useState<Dealer[]>([])
  const [region, setRegion]         = useState('all')
  const [showInactive, setInactive] = useState(false)
  const [selected, setSelected]     = useState<Dealer | null>(null)

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    fetch(`${base}data/dealers.json`).then(r => r.json()).then(setDealers)
  }, [])

  const filtered = dealers.filter(d => {
    if (!showInactive && !d.active) return false
    if (region !== 'all' && d.region !== region) return false
    return true
  })

  const regionCounts = REGIONS.map(r => ({
    region: r,
    count: dealers.filter(d => d.active && d.region === r).length,
  }))

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Bayi Haritası</h1>
        <p className="text-slate-500 text-sm mt-1">Türkiye'deki aktif bayi konumları ve bölge dağılımı</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sol panel */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Filtreler</h3>
            <div className="mb-3">
              <label className="text-xs text-slate-500 mb-1 block">Bölge</label>
              <select value={region} onChange={e => setRegion(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white">
                <option value="all">Tüm Bölgeler</option>
                {REGIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={showInactive} onChange={e => setInactive(e.target.checked)} className="rounded" />
              Pasif bayileri göster
            </label>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Bölge Dağılımı</h3>
            <div className="space-y-1">
              {regionCounts.map(({ region: r, count }) => (
                <button key={r} onClick={() => setRegion(region === r ? 'all' : r)}
                  className={`w-full flex items-center gap-2 p-2 rounded-lg text-xs transition-colors ${region === r ? 'bg-slate-100' : 'hover:bg-slate-50'}`}>
                  <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: REGION_COLORS[r] }} />
                  <span className="flex-1 text-left text-slate-700">{r}</span>
                  <span className="font-semibold text-slate-900">{count}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Özet</h3>
            <div className="space-y-2 text-sm">
              {[
                ['Toplam', dealers.length, ''],
                ['Aktif',  dealers.filter(d => d.active).length, 'text-green-600'],
                ['Pasif',  dealers.filter(d => !d.active).length, 'text-slate-400'],
                ['Gösterilen', filtered.length, 'text-blue-600'],
              ].map(([lbl, val, cls]) => (
                <div key={lbl as string} className="flex justify-between">
                  <span className="text-slate-500">{lbl}</span>
                  <span className={`font-semibold ${cls}`}>{val}</span>
                </div>
              ))}
            </div>
          </div>

          {selected && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <h3 className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-2">Seçili Bayi</h3>
              <p className="font-semibold text-slate-900 text-sm">{selected.name}</p>
              <p className="text-xs text-slate-500 mt-1">{selected.region}</p>
              <p className="text-xs text-slate-400 mt-1 font-mono">{selected.lat.toFixed(4)}, {selected.lon.toFixed(4)}</p>
              <span className={`mt-2 inline-block text-xs px-2 py-0.5 rounded-full font-medium ${selected.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                {selected.active ? 'Aktif' : 'Pasif'}
              </span>
              <button onClick={() => setSelected(null)} className="mt-2 block text-xs text-blue-500 hover:text-blue-700">Seçimi kaldır</button>
            </div>
          )}
        </div>

        {/* Harita */}
        <div className="lg:col-span-3 rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 560 }}>
          {dealers.length > 0 && (
            <MapContainer center={[39.0, 35.5]} zoom={6} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {Object.entries(REGION_POLYGONS).map(([r, pos]) => (
                <Polygon key={r} positions={pos} pathOptions={{
                  color: REGION_COLORS[r] ?? '#94a3b8',
                  fillColor: REGION_COLORS[r] ?? '#94a3b8',
                  fillOpacity: 0.12, weight: 1.5,
                }}>
                  <Tooltip sticky>{r}</Tooltip>
                </Polygon>
              ))}
              {filtered.map(d => {
                const isSelected = selected?.name === d.name
                const color = REGION_COLORS[d.region] ?? '#94a3b8'
                return (
                  <CircleMarker key={d.name} center={[d.lat, d.lon]}
                    radius={isSelected ? 12 : d.active ? 8 : 6}
                    pathOptions={{
                      color: isSelected ? '#1e40af' : color,
                      fillColor: d.active ? color : '#94a3b8',
                      fillOpacity: d.active ? 0.85 : 0.4,
                      weight: isSelected ? 3 : 1.5,
                    }}
                    eventHandlers={{ click: () => setSelected(d) }}
                  >
                    <Popup>
                      <p className="font-semibold text-sm">{d.name}</p>
                      <p className="text-xs text-slate-500">{d.region}</p>
                      <p className="text-xs text-slate-400 font-mono mt-1">{d.lat.toFixed(4)}, {d.lon.toFixed(4)}</p>
                      <span className={`mt-1 inline-block text-xs px-2 py-0.5 rounded-full ${d.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {d.active ? 'Aktif' : 'Pasif'}
                      </span>
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>
          )}
        </div>
      </div>

      {/* Tablo */}
      <div className="mt-6 bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-600">
            Bayi Listesi{region !== 'all' ? ` — ${region}` : ''} ({filtered.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                {['Bayi','Bölge','Enlem','Boylam','Durum'].map(h => (
                  <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${h === 'Enlem' || h === 'Boylam' ? 'text-right' : h === 'Durum' ? 'text-center' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...filtered].sort((a,b) => parseInt(a.name.split(' ').pop()??'0') - parseInt(b.name.split(' ').pop()??'0')).map(d => (
                <tr key={d.name} onClick={() => setSelected(d)}
                  className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${selected?.name === d.name ? 'bg-blue-50' : ''}`}>
                  <td className="px-4 py-2.5 font-medium text-slate-900">{d.name}</td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full" style={{ background: REGION_COLORS[d.region] }} />
                      <span className="text-slate-600">{d.region}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-500 font-mono text-xs">{d.lat.toFixed(4)}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500 font-mono text-xs">{d.lon.toFixed(4)}</td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${d.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'}`}>
                      {d.active ? 'Aktif' : 'Pasif'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
