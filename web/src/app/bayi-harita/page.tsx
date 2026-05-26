'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'

// ─── Types ───────────────────────────────────────────────────────────────────
interface Dealer {
  name:   string
  lat:    number
  lon:    number
  region: string
  active: boolean
}

// ─── Dynamic Leaflet import (SSR disabled) ────────────────────────────────────
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false, loading: () => (
  <div className="flex items-center justify-center h-full text-slate-400 text-sm">Harita yükleniyor…</div>
) })

// ─── Constants ────────────────────────────────────────────────────────────────
const REGION_COLORS: Record<string, string> = {
  'Marmara':              '#3b82f6',
  'Karadeniz':            '#22c55e',
  'Ege':                  '#f59e0b',
  'İç Anadolu':           '#8b5cf6',
  'Akdeniz':              '#ef4444',
  'Doğu Anadolu':         '#ec4899',
  'Güneydoğu Anadolu':    '#14b8a6',
}

const REGIONS = Object.keys(REGION_COLORS)

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function BayiHaritaPage() {
  const [dealers, setDealers]         = useState<Dealer[]>([])
  const [selectedRegion, setRegion]   = useState<string>('all')
  const [showInactive, setInactive]   = useState(false)
  const [selectedDealer, setSelected] = useState<Dealer | null>(null)

  useEffect(() => {
    fetch('/data/dealers.json')
      .then(r => r.json())
      .then(setDealers)
  }, [])

  const filtered = dealers.filter(d => {
    if (!showInactive && !d.active) return false
    if (selectedRegion !== 'all' && d.region !== selectedRegion) return false
    return true
  })

  const regionCounts = REGIONS.map(r => ({
    region: r,
    count: dealers.filter(d => d.active && d.region === r).length,
    color: REGION_COLORS[r],
  }))

  return (
    <div className="max-w-7xl mx-auto h-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Bayi Haritası</h1>
        <p className="text-slate-500 text-sm mt-1">Türkiye'deki aktif bayi konumları ve bölge dağılımı</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left panel: filters + stats */}
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Filtreler</h3>

            <div className="mb-3">
              <label className="text-xs text-slate-500 mb-1 block">Bölge</label>
              <select
                value={selectedRegion}
                onChange={e => setRegion(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white"
              >
                <option value="all">Tüm Bölgeler</option>
                {REGIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={e => setInactive(e.target.checked)}
                className="rounded"
              />
              Pasif bayileri göster
            </label>
          </div>

          {/* Region breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Bölge Dağılımı</h3>
            <div className="space-y-2">
              {regionCounts.map(({ region, count, color }) => (
                <button
                  key={region}
                  onClick={() => setRegion(selectedRegion === region ? 'all' : region)}
                  className={`w-full flex items-center gap-2 p-2 rounded-lg text-sm transition-colors ${
                    selectedRegion === region ? 'bg-slate-100' : 'hover:bg-slate-50'
                  }`}
                >
                  <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="flex-1 text-left text-slate-700 text-xs">{region}</span>
                  <span className="font-semibold text-slate-900 text-xs">{count}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Summary */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Özet</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Toplam bayi</span>
                <span className="font-semibold">{dealers.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Aktif</span>
                <span className="font-semibold text-green-600">{dealers.filter(d => d.active).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Pasif</span>
                <span className="font-semibold text-slate-400">{dealers.filter(d => !d.active).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Gösterilen</span>
                <span className="font-semibold text-blue-600">{filtered.length}</span>
              </div>
            </div>
          </div>

          {/* Selected dealer info */}
          {selectedDealer && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <h3 className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-2">Seçili Bayi</h3>
              <p className="font-semibold text-slate-900 text-sm">{selectedDealer.name}</p>
              <p className="text-xs text-slate-500 mt-1">{selectedDealer.region}</p>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                {selectedDealer.lat.toFixed(4)}, {selectedDealer.lon.toFixed(4)}
              </p>
              <span className={`mt-2 inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                selectedDealer.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
              }`}>
                {selectedDealer.active ? 'Aktif' : 'Pasif'}
              </span>
              <button
                onClick={() => setSelected(null)}
                className="mt-2 block text-xs text-blue-500 hover:text-blue-700"
              >
                Seçimi kaldır
              </button>
            </div>
          )}
        </div>

        {/* Map */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 560 }}>
          {dealers.length > 0 && (
            <MapView
              dealers={filtered}
              regionColors={REGION_COLORS}
              selectedDealer={selectedDealer}
              onSelectDealer={setSelected}
            />
          )}
        </div>
      </div>

      {/* Dealer table */}
      <div className="mt-6 bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-600">
            Bayi Listesi{selectedRegion !== 'all' ? ` — ${selectedRegion}` : ''} ({filtered.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-2.5 font-medium text-slate-500 text-xs">Bayi</th>
                <th className="text-left px-4 py-2.5 font-medium text-slate-500 text-xs">Bölge</th>
                <th className="text-right px-4 py-2.5 font-medium text-slate-500 text-xs">Enlem</th>
                <th className="text-right px-4 py-2.5 font-medium text-slate-500 text-xs">Boylam</th>
                <th className="text-center px-4 py-2.5 font-medium text-slate-500 text-xs">Durum</th>
              </tr>
            </thead>
            <tbody>
              {filtered
                .slice()
                .sort((a, b) => {
                  const na = parseInt(a.name.split(' ').pop() || '0')
                  const nb = parseInt(b.name.split(' ').pop() || '0')
                  return na - nb
                })
                .map(d => (
                  <tr
                    key={d.name}
                    className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${
                      selectedDealer?.name === d.name ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setSelected(d)}
                  >
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
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        d.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'
                      }`}>
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
