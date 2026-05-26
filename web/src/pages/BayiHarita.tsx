import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

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

const REGION_POLYGONS: Record<string, [number, number][]> = {
  'Marmara':           [[26.0,41.9],[27.5,42.0],[28.5,41.8],[29.1,41.4],[30.5,41.2],[32.0,41.5],[32.0,40.5],[30.5,40.0],[28.0,39.5],[26.5,39.5],[26.2,40.0]],
  'Karadeniz':         [[32.0,41.5],[33.5,41.7],[35.0,41.5],[36.5,41.3],[38.0,41.1],[40.5,41.3],[41.5,41.5],[43.5,41.5],[44.5,40.3],[44.0,40.5],[40.5,40.5],[38.0,40.5],[32.0,40.5]],
  'Ege':               [[26.5,39.5],[28.0,39.5],[30.5,40.0],[30.5,37.5],[30.5,36.4],[29.0,36.2],[28.0,36.5],[27.5,36.8],[27.2,37.0],[27.0,37.5],[26.5,38.3],[26.3,39.0]],
  'İç Anadolu':        [[32.0,40.5],[38.0,40.5],[38.0,37.5],[30.5,37.5],[30.5,40.0]],
  'Akdeniz':           [[30.5,37.5],[37.0,37.5],[37.0,36.7],[36.5,36.5],[36.0,36.4],[35.0,36.2],[34.0,36.0],[33.0,36.0],[31.5,36.2],[30.5,36.4]],
  'Doğu Anadolu':      [[38.0,40.5],[44.0,40.5],[44.5,40.3],[44.5,39.5],[44.5,38.5],[44.0,37.5],[38.0,37.5]],
  'Güneydoğu Anadolu': [[37.0,37.5],[38.0,37.5],[44.0,37.5],[44.3,37.2],[43.5,37.0],[42.5,36.8],[41.5,36.8],[40.5,37.1],[38.5,36.7],[37.0,36.7]],
}

const REGIONS = Object.keys(REGION_COLORS)

export default function BayiHarita() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map          = useRef<maplibregl.Map | null>(null)
  const popupRef     = useRef<maplibregl.Popup | null>(null)

  const [dealers, setDealers]       = useState<Dealer[]>([])
  const [region, setRegion]         = useState('all')
  const [showInactive, setInactive] = useState(false)
  const [selected, setSelected]     = useState<Dealer | null>(null)
  const [mapReady, setMapReady]     = useState(false)

  // Load dealers
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/dealers.json`)
      .then(r => r.json())
      .then(setDealers)
  }, [])

  // Init map
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

  // Add/update layers once map is ready and dealers loaded
  useEffect(() => {
    if (!mapReady || !map.current || dealers.length === 0) return
    const m = map.current

    // ── Region polygons ──
    Object.entries(REGION_POLYGONS).forEach(([regionName, coords]) => {
      const srcId = `region-${regionName}`
      const layerId = `region-fill-${regionName}`
      const lineId  = `region-line-${regionName}`
      if (!m.getSource(srcId)) {
        m.addSource(srcId, {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: { name: regionName },
            geometry: { type: 'Polygon', coordinates: [[...coords, coords[0]]] },
          },
        })
        m.addLayer({ id: layerId, type: 'fill', source: srcId,
          paint: { 'fill-color': REGION_COLORS[regionName] ?? '#94a3b8', 'fill-opacity': 0.12 } })
        m.addLayer({ id: lineId, type: 'line', source: srcId,
          paint: { 'line-color': REGION_COLORS[regionName] ?? '#94a3b8', 'line-width': 1.5, 'line-opacity': 0.7 } })
      }
    })

    // ── Dealer points ──
    const filtered = dealers.filter(d => (showInactive || d.active) && (region === 'all' || d.region === region))
    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: filtered.map(d => ({
        type: 'Feature',
        properties: { name: d.name, region: d.region, active: d.active, selected: selected?.name === d.name },
        geometry: { type: 'Point', coordinates: [d.lon, d.lat] },
      })),
    }

    if (m.getSource('dealers')) {
      (m.getSource('dealers') as maplibregl.GeoJSONSource).setData(geojson)
    } else {
      m.addSource('dealers', { type: 'geojson', data: geojson })

      // Shadow circle
      m.addLayer({ id: 'dealers-shadow', type: 'circle', source: 'dealers',
        paint: { 'circle-radius': 11, 'circle-color': '#000', 'circle-opacity': 0.15, 'circle-blur': 1 } })

      // Main circle
      m.addLayer({ id: 'dealers-circle', type: 'circle', source: 'dealers',
        paint: {
          'circle-radius': ['case', ['==', ['get', 'selected'], true], 13, ['==', ['get', 'active'], true], 9, 6],
          'circle-color': [
            'match', ['get', 'region'],
            'Marmara', REGION_COLORS['Marmara'],
            'Karadeniz', REGION_COLORS['Karadeniz'],
            'Ege', REGION_COLORS['Ege'],
            'İç Anadolu', REGION_COLORS['İç Anadolu'],
            'Akdeniz', REGION_COLORS['Akdeniz'],
            'Doğu Anadolu', REGION_COLORS['Doğu Anadolu'],
            'Güneydoğu Anadolu', REGION_COLORS['Güneydoğu Anadolu'],
            '#94a3b8',
          ],
          'circle-opacity': ['case', ['==', ['get', 'active'], true], 0.9, 0.45],
          'circle-stroke-width': ['case', ['==', ['get', 'selected'], true], 3, 1.5],
          'circle-stroke-color': ['case', ['==', ['get', 'selected'], true], '#1e3a8a', '#fff'],
        },
      })

      // Labels
      m.addLayer({ id: 'dealers-label', type: 'symbol', source: 'dealers',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 10,
          'text-offset': [0, 1.4],
          'text-anchor': 'top',
        },
        paint: { 'text-color': '#1e293b', 'text-halo-color': '#fff', 'text-halo-width': 1.5 },
      })

      // Click handler
      m.on('click', 'dealers-circle', (e) => {
        if (!e.features?.[0]) return
        const props = e.features[0].properties as { name: string }
        const dealer = dealers.find(d => d.name === props.name)
        if (!dealer) return
        setSelected(prev => prev?.name === dealer.name ? null : dealer)
        popupRef.current?.remove()
        popupRef.current = new maplibregl.Popup({ offset: 14, closeButton: false })
          .setLngLat([dealer.lon, dealer.lat])
          .setHTML(`
            <div style="font-family:sans-serif;min-width:140px">
              <p style="font-weight:700;margin:0 0 4px">${dealer.name}</p>
              <p style="color:#64748b;font-size:12px;margin:0 0 4px">${dealer.region}</p>
              <p style="font-family:monospace;font-size:11px;color:#94a3b8;margin:0">
                ${dealer.lat.toFixed(4)}, ${dealer.lon.toFixed(4)}
              </p>
              <span style="display:inline-block;margin-top:6px;font-size:11px;padding:2px 8px;border-radius:999px;
                background:${dealer.active ? '#dcfce7' : '#f1f5f9'};color:${dealer.active ? '#166534' : '#64748b'}">
                ${dealer.active ? 'Aktif' : 'Pasif'}
              </span>
            </div>
          `)
          .addTo(m)
      })
      m.on('mouseenter', 'dealers-circle', () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'dealers-circle', () => { m.getCanvas().style.cursor = '' })
    }
  }, [mapReady, dealers, region, showInactive, selected])

  const filtered = dealers.filter(d => (showInactive || d.active) && (region === 'all' || d.region === region))
  const regionCounts = REGIONS.map(r => ({ region: r, count: dealers.filter(d => d.active && d.region === r).length }))

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
              {[['Toplam', dealers.length, ''],['Aktif', dealers.filter(d=>d.active).length,'text-green-600'],
                ['Pasif', dealers.filter(d=>!d.active).length,'text-slate-400'],['Gösterilen', filtered.length,'text-blue-600']]
                .map(([lbl,val,cls]) => (
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
              <button onClick={() => { setSelected(null); popupRef.current?.remove() }}
                className="mt-2 block text-xs text-blue-500 hover:text-blue-700">Seçimi kaldır</button>
            </div>
          )}
        </div>

        {/* Harita */}
        <div className="lg:col-span-3 rounded-xl border border-slate-200 shadow-sm overflow-hidden bg-slate-100" style={{ height: 560 }}>
          <div ref={mapContainer} style={{ height: '100%', width: '100%' }} />
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
                  <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${['Enlem','Boylam'].includes(h)?'text-right':h==='Durum'?'text-center':'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...filtered].sort((a,b) => parseInt(a.name.split(' ').pop()??'0') - parseInt(b.name.split(' ').pop()??'0')).map(d => (
                <tr key={d.name}
                  onClick={() => setSelected(s => s?.name === d.name ? null : d)}
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
