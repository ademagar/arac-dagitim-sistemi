import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

interface FinalRow { month: number; month_name: string; final_si: number; odd_si: number; segment_si: number }
interface MevsimData {
  final:    FinalRow[]
  bayi_si:  Record<string, number | string>[]
  model_si: Record<string, number | string>[]
  renk_si:  Record<string, number | string>[]
}

const CHART_COLORS = [
  '#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6',
  '#ec4899','#14b8a6','#f97316','#6366f1','#84cc16',
  '#06b6d4','#a855f7','#e11d48','#0d9488','#d97706',
  '#2563eb','#16a34a','#dc2626',
]

function siColor(v: number) {
  if (v >= 1.15) return '#22c55e'
  if (v <= 0.85) return '#ef4444'
  return '#f59e0b'
}

function siBg(v: number) {
  if (v >= 1.15) return { background: '#dcfce7', color: '#166534' }
  if (v <= 0.85) return { background: '#fee2e2', color: '#991b1b' }
  return { background: '#fef9c3', color: '#854d0e' }
}

function TabBar({ tabs, active, onChange }: { tabs: string[]; active: number; onChange: (i: number) => void }) {
  return (
    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg mb-6 w-fit flex-wrap">
      {tabs.map((t, i) => (
        <button key={t} onClick={() => onChange(i)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${active === i ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
          {t}
        </button>
      ))}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">{title}</h3>
      {children}
    </div>
  )
}

function HeatTable({ data, keys, selected, onSelect }: {
  data: Record<string, number | string>[]
  keys: string[]
  selected: string
  onSelect: (k: string) => void
}) {
  return (
    <Card title="SI Tablosu (tıkla → grafik)">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 px-2 font-medium text-slate-500">Ad</th>
              {data.map(r => (
                <th key={r.month as number} className="text-center py-2 px-1 font-medium text-slate-500 w-14">
                  {(r.month_name as string).slice(0, 3)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k}
                onClick={() => onSelect(k)}
                className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${k === selected ? 'bg-blue-50' : ''}`}
              >
                <td className="py-1.5 px-2 font-medium text-slate-700 whitespace-nowrap">{k}</td>
                {data.map(row => {
                  const v = row[k] as number
                  return (
                    <td key={row.month as number} className="py-1.5 px-1 text-center">
                      <span className="inline-block w-12 py-0.5 rounded font-mono text-center" style={siBg(v)}>
                        {v?.toFixed(2) ?? '-'}
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
  )
}

export default function Mevsimsellik() {
  const [data, setData]     = useState<MevsimData | null>(null)
  const [tab, setTab]       = useState(0)
  const [dealer, setDealer] = useState('')
  const [model, setModel]   = useState('')

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    fetch(`${base}data/mevsimsellik.json`).then(r => r.json()).then(setData)
  }, [])

  if (!data) return <div className="flex items-center justify-center h-64 text-slate-400">Yükleniyor…</div>

  const dealerKeys = Object.keys(data.bayi_si[0]).filter(k => k !== 'month' && k !== 'month_name')
    .sort((a,b) => parseInt(a.split(' ').pop()??'0') - parseInt(b.split(' ').pop()??'0'))
  const modelKeys = Object.keys(data.model_si[0]).filter(k => k !== 'month' && k !== 'month_name').sort()
  const renkKeys  = Object.keys(data.renk_si[0]).filter(k => k !== 'month' && k !== 'month_name').sort()

  const effDealer = dealer || dealerKeys[0]
  const effModel  = model  || modelKeys[0]

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Mevsimsellik Analizi</h1>
        <p className="text-slate-500 text-sm mt-1">STL Decomposition ile hesaplanan aylık mevsimsellik indeksleri</p>
      </div>

      <TabBar tabs={['Genel SI', 'Bayi Bazında', 'Model Bazında', 'Renk Bazında']} active={tab} onChange={setTab} />

      {/* TAB 0: Genel */}
      {tab === 0 && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.final.map(row => (
              <div key={row.month} className="bg-white rounded-xl border border-slate-200 p-3 text-center">
                <p className="text-xs font-medium text-slate-500 mb-1">{row.month_name}</p>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono" style={siBg(row.final_si)}>
                  {row.final_si.toFixed(3)}
                </span>
                <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5">
                  <div className="h-1.5 rounded-full" style={{ width: `${Math.min(100, (row.final_si/2)*100)}%`, background: siColor(row.final_si) }} />
                </div>
              </div>
            ))}
          </div>

          <Card title="Final SI ve Kaynak Seriler">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={data.final} margin={{ left: 0, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <Legend />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Line dataKey="final_si"   name="Final SI"      stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4 }} />
                <Line dataKey="odd_si"     name="ODD Segment"   stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                <Line dataKey="segment_si" name="Marka Segment" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Final SI — Aylık Sütun">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.final} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey="final_si" name="Final SI" radius={[4,4,0,0]}>
                  {data.final.map(r => <Cell key={r.month} fill={siColor(r.final_si)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-xs text-slate-400 mt-2 text-center">Yeşil ≥1.15 · Sarı 0.85–1.15 · Kırmızı ≤0.85</p>
          </Card>
        </div>
      )}

      {/* TAB 1: Bayi */}
      {tab === 1 && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">Bayi:</label>
            <select value={effDealer} onChange={e => setDealer(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white">
              {dealerKeys.map(k => <option key={k}>{k}</option>)}
            </select>
          </div>
          <Card title={`${effDealer} — Aylık SI`}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.bayi_si} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey={effDealer} name="SI" radius={[4,4,0,0]}>
                  {data.bayi_si.map(r => <Cell key={r.month as number} fill={siColor(r[effDealer] as number)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <HeatTable data={data.bayi_si} keys={dealerKeys} selected={effDealer} onSelect={setDealer} />
          <Card title="Tüm Bayiler — Çizgi">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data.bayi_si} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                {dealerKeys.map((k, i) => (
                  <Line key={k} dataKey={k} stroke={CHART_COLORS[i%CHART_COLORS.length]} dot={false} strokeWidth={1.2} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 2: Model */}
      {tab === 2 && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">Model:</label>
            <select value={effModel} onChange={e => setModel(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white">
              {modelKeys.map(k => <option key={k}>{k}</option>)}
            </select>
          </div>
          <Card title={`${effModel} — Aylık SI`}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.model_si} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey={effModel} name="SI" radius={[4,4,0,0]}>
                  {data.model_si.map(r => <Cell key={r.month as number} fill={siColor(r[effModel] as number)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <HeatTable data={data.model_si} keys={modelKeys} selected={effModel} onSelect={setModel} />
          <Card title="Tüm Modeller — Çizgi">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.model_si} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                {modelKeys.map((k,i) => (
                  <Line key={k} dataKey={k} stroke={CHART_COLORS[i%CHART_COLORS.length]} dot={false} strokeWidth={1.5} />
                ))}
                <Legend />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 3: Renk */}
      {tab === 3 && (
        <div className="space-y-6">
          <HeatTable data={data.renk_si} keys={renkKeys} selected="" onSelect={() => {}} />
          <Card title="Tüm Renkler — Çizgi">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data.renk_si} margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                {renkKeys.map((k,i) => (
                  <Line key={k} dataKey={k} stroke={CHART_COLORS[i%CHART_COLORS.length]} dot={false} strokeWidth={1.5} />
                ))}
                <Legend />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  )
}
