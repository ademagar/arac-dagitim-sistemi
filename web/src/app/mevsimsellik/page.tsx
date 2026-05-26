'use client'

import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

// ─── Types ───────────────────────────────────────────────────────────────────
interface FinalRow { month: number; month_name: string; final_si: number; odd_si: number; segment_si: number }
interface BayiRow  { month: number; month_name: string; [dealer: string]: number | string }
interface ModelRow { month: number; month_name: string; [model: string]: number | string }
interface RenkRow  { month: number; month_name: string; [renk: string]: number | string }

interface MevsimData {
  final:    FinalRow[]
  bayi_si:  BayiRow[]
  model_si: ModelRow[]
  renk_si:  RenkRow[]
}

// ─── Constants ────────────────────────────────────────────────────────────────
const CHART_COLORS = [
  '#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6',
  '#ec4899','#14b8a6','#f97316','#6366f1','#84cc16',
  '#06b6d4','#a855f7','#e11d48','#0d9488','#d97706',
  '#2563eb','#16a34a','#dc2626',
]

// ─── Helpers ─────────────────────────────────────────────────────────────────
function siColor(v: number) {
  if (v >= 1.15) return '#22c55e'
  if (v <= 0.85) return '#ef4444'
  return '#f59e0b'
}

function SIBadge({ value }: { value: number }) {
  const bg = value >= 1.15 ? 'bg-green-100 text-green-700' : value <= 0.85 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
  return <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${bg}`}>{value.toFixed(3)}</span>
}

// ─── Sub-components ──────────────────────────────────────────────────────────
function Card({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-slate-200 p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-600 mb-4 uppercase tracking-wide">{title}</h3>
      {children}
    </div>
  )
}

function MultiLineChart({
  data, keys, title,
}: { data: Record<string, number | string>[]; keys: string[]; title: string }) {
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const toggle = (k: string) => setHidden(prev => { const s = new Set(prev); s.has(k) ? s.delete(k) : s.add(k); return s })
  return (
    <Card title={title}>
      {/* Legend toggles */}
      <div className="flex flex-wrap gap-2 mb-3">
        {keys.map((k, i) => (
          <button
            key={k}
            onClick={() => toggle(k)}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded border transition-opacity ${hidden.has(k) ? 'opacity-30' : ''}`}
            style={{ borderColor: CHART_COLORS[i % CHART_COLORS.length] }}
          >
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
            {k}
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
          <Tooltip formatter={(v: number) => v.toFixed(3)} />
          <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
          {keys.map((k, i) => (
            <Line
              key={k}
              dataKey={k}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              dot={false}
              strokeWidth={hidden.has(k) ? 0 : 1.5}
              hide={hidden.has(k)}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function MevsimsellikPage() {
  const [data, setData]       = useState<MevsimData | null>(null)
  const [activeTab, setTab]   = useState(0)
  const [selectedDealer, setDealer] = useState<string>('')
  const [selectedModel, setModel]   = useState<string>('')

  useEffect(() => {
    fetch('/data/mevsimsellik.json')
      .then(r => r.json())
      .then(setData)
  }, [])

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Yükleniyor...
      </div>
    )
  }

  // Derived keys
  const dealerKeys = Object.keys(data.bayi_si[0]).filter(k => k !== 'month' && k !== 'month_name').sort((a, b) => {
    const na = parseInt(a.split(' ').pop() || '0')
    const nb = parseInt(b.split(' ').pop() || '0')
    return na - nb
  })
  const modelKeys = Object.keys(data.model_si[0]).filter(k => k !== 'month' && k !== 'month_name').sort()
  const renkKeys  = Object.keys(data.renk_si[0]).filter(k => k !== 'month' && k !== 'month_name').sort()

  const effectiveDealer = selectedDealer || dealerKeys[0]
  const effectiveModel  = selectedModel  || modelKeys[0]

  const tabs = ['Genel SI', 'Bayi Bazında', 'Model Bazında', 'Renk Bazında']

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Mevsimsellik Analizi</h1>
        <p className="text-slate-500 text-sm mt-1">STL Decomposition ile hesaplanan aylık mevsimsellik indeksleri</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-lg mb-6 w-fit">
        {tabs.map((t, i) => (
          <button
            key={t}
            onClick={() => setTab(i)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === i ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* TAB 0: Genel SI */}
      {activeTab === 0 && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.final.map(row => (
              <div key={row.month} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
                <p className="text-xs font-medium text-slate-500 mb-1">{row.month_name}</p>
                <div className="flex justify-center mb-1">
                  <SIBadge value={row.final_si} />
                </div>
                <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full"
                    style={{
                      width: `${Math.min(100, (row.final_si / 2) * 100)}%`,
                      background: siColor(row.final_si),
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Line chart: all 3 series */}
          <Card title="Final SI ve Kaynak Seriler">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={data.final} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <Legend />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: 'SI=1', position: 'right', fontSize: 10 }} />
                <Line dataKey="final_si"    name="Final SI"    stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4 }} />
                <Line dataKey="odd_si"      name="ODD Segment" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                <Line dataKey="segment_si"  name="Marka Segment" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* Bar chart: final_si */}
          <Card title="Final Mevsimsellik İndeksi — Aylık">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.final} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey="final_si" name="Final SI" radius={[4, 4, 0, 0]}>
                  {data.final.map(row => (
                    <Cell key={row.month} fill={siColor(row.final_si)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-xs text-slate-400 mt-2 text-center">
              Yeşil ≥ 1.15 (yüksek sezon) · Sarı 0.85–1.15 (normal) · Kırmızı ≤ 0.85 (düşük sezon)
            </p>
          </Card>
        </div>
      )}

      {/* TAB 1: Bayi Bazında */}
      {activeTab === 1 && (
        <div className="space-y-6">
          {/* Dealer selector */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">Bayi Seç:</label>
            <select
              value={effectiveDealer}
              onChange={e => setDealer(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
            >
              {dealerKeys.map(k => <option key={k}>{k}</option>)}
            </select>
          </div>

          {/* Selected dealer line chart */}
          <Card title={`${effectiveDealer} — Aylık SI`}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.bayi_si} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey={effectiveDealer} name="SI" radius={[4, 4, 0, 0]}>
                  {data.bayi_si.map(row => (
                    <Cell key={row.month} fill={siColor(row[effectiveDealer] as number)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* All dealers heatmap-style table */}
          <Card title="Tüm Bayiler — SI Tablosu">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 font-medium text-slate-500 whitespace-nowrap">Bayi</th>
                    {data.bayi_si.map(r => (
                      <th key={r.month} className="text-center py-2 px-1 font-medium text-slate-500 whitespace-nowrap w-14">
                        {r.month_name.slice(0, 3)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dealerKeys.map(dealer => (
                    <tr
                      key={dealer}
                      className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${dealer === effectiveDealer ? 'bg-blue-50' : ''}`}
                      onClick={() => setDealer(dealer)}
                    >
                      <td className="py-1.5 px-2 font-medium text-slate-700 whitespace-nowrap">{dealer}</td>
                      {data.bayi_si.map(row => {
                        const v = row[dealer] as number
                        return (
                          <td key={row.month} className="py-1.5 px-1 text-center">
                            <span
                              className="inline-block w-12 py-0.5 rounded text-center font-mono"
                              style={{
                                background: v >= 1.15 ? '#dcfce7' : v <= 0.85 ? '#fee2e2' : '#fef9c3',
                                color:      v >= 1.15 ? '#166534' : v <= 0.85 ? '#991b1b' : '#854d0e',
                              }}
                            >
                              {v.toFixed(2)}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* All dealers multi-line */}
          <MultiLineChart data={data.bayi_si as Record<string, number | string>[]} keys={dealerKeys} title="Tüm Bayiler — Çizgi Grafik" />
        </div>
      )}

      {/* TAB 2: Model Bazında */}
      {activeTab === 2 && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">Model Seç:</label>
            <select
              value={effectiveModel}
              onChange={e => setModel(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
            >
              {modelKeys.map(k => <option key={k}>{k}</option>)}
            </select>
          </div>

          <Card title={`${effectiveModel} — Aylık SI`}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.model_si} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey={effectiveModel} name="SI" radius={[4, 4, 0, 0]}>
                  {data.model_si.map(row => (
                    <Cell key={row.month} fill={siColor(row[effectiveModel] as number)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* Model SI table */}
          <Card title="Tüm Modeller — SI Tablosu">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 font-medium text-slate-500">Model</th>
                    {data.model_si.map(r => (
                      <th key={r.month} className="text-center py-2 px-1 font-medium text-slate-500 w-14">
                        {r.month_name.slice(0, 3)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {modelKeys.map(model => (
                    <tr
                      key={model}
                      className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 ${model === effectiveModel ? 'bg-blue-50' : ''}`}
                      onClick={() => setModel(model)}
                    >
                      <td className="py-1.5 px-2 font-medium text-slate-700">{model}</td>
                      {data.model_si.map(row => {
                        const v = row[model] as number
                        return (
                          <td key={row.month} className="py-1.5 px-1 text-center">
                            <span
                              className="inline-block w-12 py-0.5 rounded font-mono"
                              style={{
                                background: v >= 1.15 ? '#dcfce7' : v <= 0.85 ? '#fee2e2' : '#fef9c3',
                                color:      v >= 1.15 ? '#166534' : v <= 0.85 ? '#991b1b' : '#854d0e',
                              }}
                            >
                              {v.toFixed(2)}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <MultiLineChart data={data.model_si as Record<string, number | string>[]} keys={modelKeys} title="Tüm Modeller — Çizgi Grafik" />
        </div>
      )}

      {/* TAB 3: Renk Bazında */}
      {activeTab === 3 && (
        <div className="space-y-6">
          {/* Renk SI table */}
          <Card title="Tüm Renkler — SI Tablosu">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 font-medium text-slate-500">Renk</th>
                    {data.renk_si.map(r => (
                      <th key={r.month} className="text-center py-2 px-1 font-medium text-slate-500 w-14">
                        {r.month_name.slice(0, 3)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {renkKeys.map(renk => (
                    <tr key={renk} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-1.5 px-2 font-medium text-slate-700">{renk}</td>
                      {data.renk_si.map(row => {
                        const v = row[renk] as number
                        return (
                          <td key={row.month} className="py-1.5 px-1 text-center">
                            <span
                              className="inline-block w-12 py-0.5 rounded font-mono"
                              style={{
                                background: v >= 1.15 ? '#dcfce7' : v <= 0.85 ? '#fee2e2' : '#fef9c3',
                                color:      v >= 1.15 ? '#166534' : v <= 0.85 ? '#991b1b' : '#854d0e',
                              }}
                            >
                              {v.toFixed(2)}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <MultiLineChart data={data.renk_si as Record<string, number | string>[]} keys={renkKeys} title="Tüm Renkler — Çizgi Grafik" />
        </div>
      )}
    </div>
  )
}
