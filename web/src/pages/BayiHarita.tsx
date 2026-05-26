import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

interface Dealer {
  name: string; code: string; lat: number; lon: number
  region: string; active: boolean
  activity: Record<string, string>
}

const REGION_COLORS: Record<string, string> = {
  'Marmara':           '#3b82f6',
  'Karadeniz':         '#22c55e',
  'Ege':               '#f59e0b',
  'İç Anadolu':        '#8b5cf6',
  'Akdeniz':           '#ef4444',
  'Doğu Anadolu':      '#ec4899',
  'Güneydoğu Anadolu': '#14b8a6',
}

const ACTIVITY_MONTHS = ['Ara.25','Oca.26','Şub.26','Mar.26','Nis.26','May.26']
const REGIONS = Object.keys(REGION_COLORS)

function statusLabel(s: string) {
  if (s === 'AKTİF') return 'Aktif'
  if (s === 'KAPANDI') return 'Kapandı'
  return 'Aktif Değil'
}

function isActive(status: string) { return status === 'AKTİF' }

export default function BayiHarita() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map          = useRef<maplibregl.Map | null>(null)
  const popupRef     = useRef<maplibregl.Popup | null>(null)

  const [dealers, setDealers]       = useState<Dealer[]>([])
  const [region, setRegion]         = useState('all')
  const [selectedMonth, setMonth]   = useState('Oca.26')
  const [showInactive, setInactive] = useState(false)
  const [selected, setSelected]     = useState<Dealer | null>(null)
  const [mapReady, setMapReady]     = useState(false)

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/dealers.json`)
      .then(r => r.json())
      .then(setDealers)
  }, [])

  useEffect(() => {
    if (!mapContainer.current || map.current) return
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [35.5, 39.0],
      zoom: 5.5,
    })
    map.current.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.current.on('load', () => setMapReady(true))
    return () => { map.current?.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (!mapReady || !map.current || dealers.length === 0) return
    const m = map.current

    const filtered = dealers.filter(d => {
      const status = d.activity[selectedMonth] ?? 'AKTİF DEĞİL'
      if (!showInactive && !isActive(status)) return false
      if (region !== 'all' && d.region !== region) return false
      return true
    })

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: filtered.map(d => {
        const status = d.activity[selectedMonth] ?? 'AKTİF DEĞİL'
        return {
          type: 'Feature',
          properties: {
            name: d.name, code: d.code, region: d.region,
            status, active: isActive(status),
            selected: selected?.name === d.name,
          },
          geometry: { type: 'Point', coordinates: [d.lon, d.lat] },
        }
      }),
    }

    if (m.getSource('dealers')) {
      (m.getSource('dealers') as maplibregl.GeoJSONSource).setData(geojson)
    } else {
      m.addSource('dealers', { type: 'geojson', data: geojson })

      m.addLayer({ id: 'dealers-shadow', type: 'circle', source: 'dealers',
        paint: { 'circle-radius': 11, 'circle-color': '#000', 'circle-opacity': 0.10, 'circle-blur': 1 } })

      m.addLayer({ id: 'dealers-circle', type: 'circle', source: 'dealers',
        paint: {
          'circle-radius': ['case', ['==', ['get', 'selected'], true], 13, ['==', ['get', 'active'], true], 9, 6],
          'circle-color': [
            'case',
            ['==', ['get', 'active'], false], '#94a3b8',
            ['match', ['get', 'region'],
              'Marmara',           REGION_COLORS['Marmara'],
              'Karadeniz',         REGION_COLORS['Karadeniz'],
              'Ege',               REGION_COLORS['Ege'],
              'İç Anadolu',        REGION_COLORS['İç Anadolu'],
              'Akdeniz',           REGION_COLORS['Akdeniz'],
              'Doğu Anadolu',      REGION_COLORS['Doğu Anadolu'],
              'Güneydoğu Anadolu', REGION_COLORS['Güneydoğu Anadolu'],
              '#94a3b8',
            ],
          ],
          'circle-opacity': ['case', ['==', ['get', 'active'], true], 0.9, 0.4],
          'circle-stroke-width': ['case', ['==', ['get', 'selected'], true], 3, 1.5],
          'circle-stroke-color': ['case',
            ['==', ['get', 'selected'], true], '#1e3a8a',
            ['==', ['get', 'active'], true], '#fff',
            '#cbd5e1',
          ],
        },
      })

      m.addLayer({ id: 'dealers-label', type: 'symbol', source: 'dealers',
        layout: { 'text-field': ['get', 'name'], 'text-size': 10, 'text-offset': [0, 1.4], 'text-anchor': 'top' },
        paint: { 'text-color': '#1e293b', 'text-halo-color': '#fff', 'text-halo-width': 1.5 },
      })

      m.on('click', 'dealers-circle', (e) => {
        if (!e.features?.[0]) return
        const props = e.features[0].properties as { name: string }
        const dealer = dealers.find(d => d.name === props.name)
        if (!dealer) return
        setSelected(prev => prev?.name === dealer.name ? null : dealer)
        const status = dealer.activity[selectedMonth] ?? 'AKTİF DEĞİL'
        const active = isActive(status)
        popupRef.current?.remove()
        popupRef.current = new maplibregl.Popup({ offset: 14, closeButton: false })
          .setLngLat([dealer.lon, dealer.lat])
          .setHTML(`
            <div style="font-family:sans-serif;min-width:160px">
              <p style="font-weight:700;margin:0 0 2px">${dealer.name}</p>
              <p style="color:#64748b;font-size:11px;margin:0 0 2px">${dealer.code}</p>
              <p style="color:#64748b;font-size:12px;margin:0 0 4px">${dealer.region}</p>
              <p style="font-family:monospace;font-size:10px;color:#94a3b8;margin:0 0 6px">
                ${dealer.lat.toFixed(4)}, ${dealer.lon.toFixed(4)}
              </p>
              <span style="font-size:11px;padding:2px 8px;border-radius:999px;
                background:${active ? '#dcfce7' : status === 'KAPANDI' ? '#fee2e2' : '#f1f5f9'};
                color:${active ? '#166534' : status === 'KAPANDI' ? '#991b1b' : '#64748b'}">
                ${status} (${selectedMonth})
              </span>
            </div>
          `)
          .addTo(m)
      })
      m.on('mouseenter', 'dealers-circle', () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'dealers-circle', () => { m.getCanvas().style.cursor = '' })
    }
  }, [mapReady, dealers, region, showInactive, selected, selectedMonth])

  // Derived counts for selected month
  const filtered = dealers.filter(d => {
    const status = d.activity[selectedMonth] ?? 'AKTİF DEĞİL'
    if (!showInactive && !isActive(status)) return false
    if (region !== 'all' && d.region !== region) return false
    return true
  })

  const activeCount   = dealers.filter(d => isActive(d.activity[selectedMonth] ?? '')).length
  const inactiveCount = dealers.filter(d => !isActive(d.activity[selectedMonth] ?? '')).length

  const regionCounts = REGIONS.map(r => ({
    region: r,
    count: dealers.filter(d => d.region === r && isActive(d.activity[selectedMonth] ?? '')).length,
  }))

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Bayi Haritası</h1>
        <p className="text-slate-500 text-sm mt-1">Türkiye'deki bayi konumları ve aylık aktiflik durumları</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sol panel */}
        <div className="space-y-4">

          {/* Ay seçici */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Ay Seç</h3>
            <div className="grid grid-cols-3 gap-1">
              {ACTIVITY_MONTHS.map(m => (
                <button key={m} onClick={() => setMonth(m)}
                  className={`py-1.5 rounded-lg text-xs font-medium transition-colors ${selectedMonth === m ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                  {m}
                </button>
              ))}
            </div>
            <div className="mt-3 flex gap-3 text-xs">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block"/>Aktif: {activeCount}</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-300 inline-block"/>Pasif/Kapandı: {inactiveCount}</span>
            </div>
          </div>

          {/* Filtreler */}
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
              Pasif / Kapandı bayileri göster
            </label>
          </div>

          {/* Bölge dağılımı */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Bölge ({selectedMonth})</h3>
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

          {/* Seçili bayi */}
          {selected && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <h3 className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-2">Seçili Bayi</h3>
              <p className="font-semibold text-slate-900 text-sm">{selected.name}</p>
              <p className="text-xs text-blue-600 font-mono mt-0.5">{selected.code}</p>
              <p className="text-xs text-slate-500 mt-1">{selected.region}</p>
              <p className="text-xs text-slate-400 mt-1 font-mono">{selected.lat.toFixed(4)}, {selected.lon.toFixed(4)}</p>
              <div className="mt-2 space-y-0.5">
                {ACTIVITY_MONTHS.map(m => {
                  const s = selected.activity[m] ?? 'AKTİF DEĞİL'
                  return (
                    <div key={m} className="flex justify-between text-xs">
                      <span className={`font-medium ${m === selectedMonth ? 'text-blue-700' : 'text-slate-400'}`}>{m}</span>
                      <span className={`px-1.5 rounded ${s === 'AKTİF' ? 'bg-green-100 text-green-700' : s === 'KAPANDI' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                        {statusLabel(s)}
                      </span>
                    </div>
                  )
                })}
              </div>
              <button onClick={() => { setSelected(null); popupRef.current?.remove() }}
                className="mt-3 block text-xs text-blue-500 hover:text-blue-700">Seçimi kaldır</button>
            </div>
          )}
        </div>

        {/* Harita */}
        <div className="lg:col-span-3 rounded-xl border border-slate-200 shadow-sm overflow-hidden bg-slate-100" style={{ height: 580 }}>
          <div ref={mapContainer} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>

      {/* Tablo */}
      <div className="mt-6 bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-slate-600">
            Bayi Listesi — {selectedMonth}{region !== 'all' ? ` · ${region}` : ''} ({filtered.length} gösteriliyor)
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                {['Bayi','Kod','Bölge','Enlem','Boylam','Durum'].map(h => (
                  <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${['Enlem','Boylam'].includes(h)?'text-right':h==='Durum'?'text-center':'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...filtered].sort((a,b) => parseInt(a.name.split(' ').pop()??'0') - parseInt(b.name.split(' ').pop()??'0')).map(d => {
                const status = d.activity[selectedMonth] ?? 'AKTİF DEĞİL'
                const active = isActive(status)
                return (
                  <tr key={d.name} onClick={() => setSelected(s => s?.name === d.name ? null : d)}
                    className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${selected?.name === d.name ? 'bg-blue-50' : ''}`}>
                    <td className="px-4 py-2.5 font-medium text-slate-900">{d.name}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{d.code}</td>
                    <td className="px-4 py-2.5">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ background: REGION_COLORS[d.region] ?? '#94a3b8' }} />
                        <span className="text-slate-600">{d.region}</span>
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-500 font-mono text-xs">{d.lat.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-500 font-mono text-xs">{d.lon.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${active ? 'bg-green-100 text-green-700' : status === 'KAPANDI' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-400'}`}>
                        {statusLabel(status)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
