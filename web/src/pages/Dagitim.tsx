import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, LabelList, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'

// ─── Types ────────────────────────────────────────────────────────────────────
interface AllocRow   { dealer: string; model: string; color: string; quantity: number; composite_score: number; p_score: number; s_score: number; h_score: number; lp_score: number }
interface SummaryRow { dealer: string; target: number; allocated: number; gap: number; fill_rate: number }
interface ScoreRow   { dealer: string; p_score: number; s_score: number; h_score: number; lp_score: number; composite_score: number }
interface InvRow     { model: string; color: string; total: number; used: number; remaining: number; usage_rate: number }

interface DagitimData {
  month: string
  total_inventory: number
  total_allocated: number
  allocation: AllocRow[]
  summary:    SummaryRow[]
  scores:     ScoreRow[]
  inventory:  InvRow[]
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
const SCORE_COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#06b6d4','#a855f7']

function numSort(a: string, b: string) {
  return parseInt(a.match(/\d+$/)?.[0]??'0') - parseInt(b.match(/\d+$/)?.[0]??'0')
}

function Card({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-slate-200 p-5 ${className}`}>
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">{title}</h3>
      {children}
    </div>
  )
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

function FillBadge({ pct }: { pct: number }) {
  const ok = pct >= 90 && pct <= 120
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
      {pct.toFixed(1)}%
    </span>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Dagitim() {
  const [data, setData]         = useState<DagitimData | null>(null)
  const [tab, setTab]           = useState(0)
  const [dealerFilter, setDF]   = useState<string[]>([])
  const [modelFilter, setMF]    = useState<string[]>([])
  const [selectedDealer, setSD] = useState<string>('')

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/dagitim.json`).then(r => r.json()).then(setData)
  }, [])

  if (!data) return <div className="flex items-center justify-center h-64 text-slate-400">Yükleniyor…</div>

  // Derived
  const dealers  = [...new Set(data.allocation.map(r => r.dealer))].sort(numSort)
  const models   = [...new Set(data.allocation.map(r => r.model))].sort()
  const fillRate = data.total_allocated / data.total_inventory * 100

  // Summary sorted
  const summarySorted = [...data.summary].sort((a,b) => numSort(a.dealer, b.dealer))

  // Allocation filtered
  const allocFiltered = data.allocation.filter(r =>
    (dealerFilter.length === 0 || dealerFilter.includes(r.dealer)) &&
    (modelFilter.length === 0  || modelFilter.includes(r.model))
  )

  // Bayi × Model pivot for heatmap chart
  const pivotData = summarySorted.map(s => {
    const row: Record<string, unknown> = { dealer: s.dealer }
    models.forEach(m => {
      row[m] = data.allocation.filter(r => r.dealer === s.dealer && r.model === m).reduce((acc,r) => acc + r.quantity, 0)
    })
    return row
  })

  // Score radar for selected dealer
  const effDealer = selectedDealer || dealers[0]
  const dealerScore = data.scores.find(s => s.dealer === effDealer)
  const radarData = dealerScore ? [
    { subject: 'Performans (P)', value: dealerScore.p_score,         fullMark: 1 },
    { subject: 'LP Uyum',       value: dealerScore.lp_score,        fullMark: 1 },
    { subject: 'Mevsimsel (S)', value: dealerScore.s_score,         fullMark: 1 },
    { subject: 'Hedef (H)',     value: dealerScore.h_score,         fullMark: 1 },
    { subject: 'Bileşik',      value: dealerScore.composite_score,  fullMark: 1 },
  ] : []

  // Inventory model summary
  const invByModel = models.map(m => {
    const rows = data.inventory.filter(r => r.model === m)
    return {
      model: m,
      total: rows.reduce((s,r) => s + r.total, 0),
      used:  rows.reduce((s,r) => s + r.used, 0),
      remaining: rows.reduce((s,r) => s + r.remaining, 0),
    }
  })

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900">Dağıtım Sistemi</h1>
          <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1 rounded-full">{data.month}</span>
        </div>
        <p className="text-slate-500 text-sm mt-1">MILP optimizasyonu ile hesaplanan optimal araç dağıtım sonuçları</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Toplam Envanter',   value: data.total_inventory.toLocaleString('tr'), sub: 'araç', color: 'text-slate-900' },
          { label: 'Toplam Atanan',     value: data.total_allocated.toLocaleString('tr'), sub: 'araç', color: 'text-blue-600' },
          { label: 'Doluluk Oranı',     value: `%${fillRate.toFixed(1)}`, sub: 'envanter kullanımı', color: fillRate >= 85 ? 'text-green-600' : 'text-red-600' },
          { label: 'Aktif Bayi',        value: dealers.length.toString(), sub: 'bayiye dağıtıldı', color: 'text-slate-900' },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <p className="text-xs text-slate-500 mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-slate-400 mt-1">{k.sub}</p>
          </div>
        ))}
      </div>

      <TabBar
        tabs={['Dağıtım Tablosu', 'Bayi Özeti', 'Model Dağılımı', 'Skor Analizi', 'Envanter Kullanımı']}
        active={tab}
        onChange={setTab}
      />

      {/* TAB 0: Dağıtım Tablosu */}
      {tab === 0 && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap gap-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Bayi Filtrele</label>
              <select multiple value={dealerFilter} onChange={e => setDF([...e.target.selectedOptions].map(o => o.value))}
                className="text-xs border border-slate-300 rounded-lg px-2 py-1 bg-white min-w-36 h-20">
                {dealers.map(d => <option key={d}>{d}</option>)}
              </select>
              {dealerFilter.length > 0 && <button onClick={() => setDF([])} className="text-xs text-blue-500 mt-1 block">Temizle</button>}
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Model Filtrele</label>
              <select multiple value={modelFilter} onChange={e => setMF([...e.target.selectedOptions].map(o => o.value))}
                className="text-xs border border-slate-300 rounded-lg px-2 py-1 bg-white min-w-28 h-20">
                {models.map(m => <option key={m}>{m}</option>)}
              </select>
              {modelFilter.length > 0 && <button onClick={() => setMF([])} className="text-xs text-blue-500 mt-1 block">Temizle</button>}
            </div>
            <div className="flex items-end">
              <p className="text-xs text-slate-400">{allocFiltered.length} satır gösteriliyor</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
                  <tr>
                    {['Bayi','Model','Renk','Adet','Bileşik Skor','P Skoru','S Skoru','H Skoru','LP Skoru'].map(h => (
                      <th key={h} className={`px-3 py-2.5 font-medium text-slate-500 text-xs whitespace-nowrap ${h==='Adet'?'text-right':'text-left'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...allocFiltered].sort((a,b) => numSort(a.dealer,b.dealer)).map((r, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-800 whitespace-nowrap">{r.dealer}</td>
                      <td className="px-3 py-2 text-slate-600">{r.model}</td>
                      <td className="px-3 py-2 text-slate-600">{r.color}</td>
                      <td className="px-3 py-2 text-right font-semibold text-slate-900">{r.quantity}</td>
                      <td className="px-3 py-2"><span className="font-mono text-blue-600">{r.composite_score.toFixed(3)}</span></td>
                      <td className="px-3 py-2 font-mono text-slate-500">{r.p_score.toFixed(3)}</td>
                      <td className="px-3 py-2 font-mono text-slate-500">{r.s_score.toFixed(3)}</td>
                      <td className="px-3 py-2 font-mono text-slate-500">{r.h_score.toFixed(3)}</td>
                      <td className="px-3 py-2 font-mono text-slate-500">{r.lp_score.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 1: Bayi Özeti */}
      {tab === 1 && (
        <div className="space-y-6">
          <Card title="Hedef vs Atanan">
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={summarySorted} margin={{ left: 0, right: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="target"    name="Hedef"   fill="#94a3b8" radius={[4,4,0,0]} />
                <Bar dataKey="allocated" name="Atanan"  radius={[4,4,0,0]}>
                  {summarySorted.map((r,i) => <Cell key={i} fill={r.fill_rate >= 90 && r.fill_rate <= 120 ? '#22c55e' : '#ef4444'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-600">Bayi Dağıtım Özeti</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    {['Bayi','Hedef','Atanan','Fark','Doluluk'].map(h => (
                      <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${['Hedef','Atanan','Fark'].includes(h)?'text-right':h==='Doluluk'?'text-center':'text-left'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {summarySorted.map(r => (
                    <tr key={r.dealer} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-900">{r.dealer}</td>
                      <td className="px-4 py-2.5 text-right text-slate-600">{r.target}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-slate-900">{r.allocated}</td>
                      <td className={`px-4 py-2.5 text-right font-semibold ${r.gap >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.gap >= 0 ? '+' : ''}{r.gap}
                      </td>
                      <td className="px-4 py-2.5 text-center"><FillBadge pct={r.fill_rate} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Model Dağılımı */}
      {tab === 2 && (
        <div className="space-y-6">
          <Card title="Bayi × Model Dağılımı (Stacked)">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={pivotData} margin={{ left: 0, right: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {models.map((m, i) => (
                  <Bar key={m} dataKey={m} stackId="a" fill={SCORE_COLORS[i % SCORE_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Model Bazında Toplam Atama">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={models.map(m => ({
                  model: m,
                  atanan: data.allocation.filter(r => r.model === m).reduce((s,r) => s + r.quantity, 0),
                })).sort((a,b) => b.atanan - a.atanan)}
                layout="vertical" margin={{ left: 20, right: 50 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="model" tick={{ fontSize: 12 }} width={40} />
                <Tooltip />
                <Bar dataKey="atanan" name="Atanan" radius={[0,4,4,0]}>
                  {models.map((_,i) => <Cell key={i} fill={SCORE_COLORS[i % SCORE_COLORS.length]} />)}
                  <LabelList dataKey="atanan" position="right" style={{ fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 3: Skor Analizi */}
      {tab === 3 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Dealer selector + radar */}
            <Card title="Bayi Skor Radari">
              <div className="mb-4">
                <select value={effDealer} onChange={e => setSD(e.target.value)}
                  className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white w-full">
                  {dealers.map(d => <option key={d}>{d}</option>)}
                </select>
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0,1]} tick={{ fontSize: 9 }} />
                  <Radar name={effDealer} dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            </Card>

            {/* Composite score bar */}
            <Card title="Bileşik Skor Sıralaması">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={[...data.scores].sort((a,b) => b.composite_score - a.composite_score).slice(0,15)}
                  layout="vertical" margin={{ left: 20, right: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 10 }} domain={[0, 1]} />
                  <YAxis type="category" dataKey="dealer" tick={{ fontSize: 10 }} width={60} />
                  <Tooltip formatter={(v: number) => v.toFixed(3)} />
                  <Bar dataKey="composite_score" name="Bileşik Skor" radius={[0,4,4,0]}>
                    {data.scores.map((_,i) => <Cell key={i} fill={SCORE_COLORS[i % SCORE_COLORS.length]} />)}
                    <LabelList dataKey="composite_score" position="right" formatter={(v: number) => v.toFixed(3)} style={{ fontSize: 10 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Score table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-600">Skor Detayı</h3>
              <p className="text-xs text-slate-400 mt-0.5">P×0.25 + LP×0.35 + S×0.20 + H×0.20</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    {['Bayi','P (Performans)','LP (Uyum)','S (Mevsim)','H (Hedef)','Bileşik'].map(h => (
                      <th key={h} className="px-4 py-2.5 font-medium text-slate-500 text-xs text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...data.scores].sort((a,b) => numSort(a.dealer,b.dealer)).map(r => (
                    <tr key={r.dealer} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-900">{r.dealer}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-600">{r.p_score.toFixed(3)}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-600">{r.lp_score.toFixed(3)}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-600">{r.s_score.toFixed(3)}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-600">{r.h_score.toFixed(3)}</td>
                      <td className="px-4 py-2.5">
                        <span className="font-mono font-semibold text-blue-600">{r.composite_score.toFixed(3)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Envanter Kullanımı */}
      {tab === 4 && (
        <div className="space-y-6">
          <Card title="Model Bazında Envanter Kullanımı">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={invByModel} margin={{ left: 0, right: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="model" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="total"     name="Toplam"  fill="#e2e8f0" radius={[4,4,0,0]} />
                <Bar dataKey="used"      name="Atanan"  fill="#3b82f6" radius={[4,4,0,0]} />
                <Bar dataKey="remaining" name="Kalan"   fill="#f59e0b" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-600">Envanter Detayı</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    {['Model','Renk','Toplam','Atanan','Kalan','Kullanım'].map(h => (
                      <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${['Toplam','Atanan','Kalan'].includes(h)?'text-right':h==='Kullanım'?'text-center':'text-left'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.inventory.map((r, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-900">{r.model}</td>
                      <td className="px-4 py-2.5 text-slate-600">{r.color}</td>
                      <td className="px-4 py-2.5 text-right text-slate-600">{r.total}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-blue-600">{r.used}</td>
                      <td className="px-4 py-2.5 text-right text-amber-600">{r.remaining}</td>
                      <td className="px-4 py-2.5 text-center">
                        <div className="flex items-center gap-2 justify-center">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${r.usage_rate}%` }} />
                          </div>
                          <span className="text-xs font-mono text-slate-600">{r.usage_rate}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
