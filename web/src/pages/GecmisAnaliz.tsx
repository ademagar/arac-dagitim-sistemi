import { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, LabelList, ReferenceLine,
} from 'recharts'

// ─── Types ────────────────────────────────────────────────────────────────────
interface SalesData {
  model:     { model: string; satis: number; pay: number }[]
  renk:      { renk: string; satis: number; pay: number }[]
  bayi:      { dealer: string; satis: number }[]
  aylik:     { period: string; satis: number; year_month: string }[]
  bayi_renk: { dealer: string; renk: string; n: number }[]
  top3_renk: { dealer: string; renk1: string; adet1: number; renk2: string; adet2: number; renk3: string; adet3: number }[]
}
interface HedefRow { period: string; hedef: number; gercek: number; pct: number }
interface RakipRow { marka: string; year_month: string; period: string; satis: number }

const YEAR_OPTS = [
  { key: '2024', label: '2024' },
  { key: '2025', label: '2025' },
  { key: 'all',  label: '2024 + 2025' },
]

const CHART_COLORS = [
  '#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6',
  '#ec4899','#14b8a6','#f97316','#6366f1','#84cc16',
  '#06b6d4','#a855f7','#e11d48','#0d9488','#d97706',
  '#2563eb','#16a34a','#dc2626',
]

function numSort(a: string, b: string) {
  const na = parseInt(a.match(/\d+$/)?.[0] ?? '0')
  const nb = parseInt(b.match(/\d+$/)?.[0] ?? '0')
  return na - nb
}

// ─── Small shared components ──────────────────────────────────────────────────
function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">{title}</h3>
      {children}
    </div>
  )
}

function TabBar({ tabs, active, onChange }: { tabs: string[]; active: number; onChange: (i: number) => void }) {
  return (
    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg mb-6 w-fit flex-wrap">
      {tabs.map((t, i) => (
        <button
          key={t}
          onClick={() => onChange(i)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            active === i ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function GecmisAnaliz() {
  const [yearKey, setYear]   = useState('2025')
  const [sales, setSales]    = useState<SalesData | null>(null)
  const [hedef, setHedef]    = useState<Record<string, HedefRow[]> | null>(null)
  const [rakip, setRakip]    = useState<RakipRow[] | null>(null)
  const [tab, setTab]        = useState(0)

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    Promise.all([
      fetch(`${base}data/sales-${yearKey}.json`).then(r => r.json()),
      fetch(`${base}data/hedef.json`).then(r => r.json()),
      fetch(`${base}data/rakip.json`).then(r => r.json()),
    ]).then(([s, h, r]) => { setSales(s); setHedef(h); setRakip(r) })
  }, [yearKey])

  if (!sales || !hedef || !rakip) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Yükleniyor…</div>
  }

  // Derived
  const hedefRows: HedefRow[] = hedef[yearKey] ?? []
  const rakipFiltered = yearKey === 'all'
    ? rakip
    : rakip.filter(r => r.year_month.startsWith(yearKey))
  const rakipMarkas = [...new Set(rakipFiltered.map(r => r.marka))].sort()
  const rakipPeriods = [...new Set(rakipFiltered.map(r => r.period))].sort()
  const rakipChart = rakipPeriods.map(p => {
    const row: Record<string, unknown> = { period: p }
    rakipMarkas.forEach(m => {
      row[m] = rakipFiltered.find(r => r.period === p && r.marka === m)?.satis ?? 0
    })
    return row
  })

  // Stacked bar data for bayi×renk
  const dealerOrder = [...sales.bayi].sort((a,b) => numSort(a.dealer, b.dealer)).map(d => d.dealer)
  const allColors = [...new Set(sales.bayi_renk.map(r => r.renk))].sort()
  const stackedData = dealerOrder.map(dealer => {
    const row: Record<string, unknown> = { dealer }
    allColors.forEach(c => {
      row[c] = sales.bayi_renk.find(r => r.dealer === dealer && r.renk === c)?.n ?? 0
    })
    return row
  })

  const tabs = ['Model & Versiyon', 'Renk & Bayi', 'Aylık Trend', 'Hedef Gerçekleşme', 'Rakip Karşılaştırma']

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Geçmiş Satış Analizi</h1>
          <p className="text-slate-500 text-sm mt-1">Bayi ve ürün bazında geçmiş satış performansı</p>
        </div>
        <div className="flex gap-2">
          {YEAR_OPTS.map(o => (
            <button
              key={o.key}
              onClick={() => setYear(o.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                yearKey === o.key
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {/* TAB 0: Model & Versiyon */}
      {tab === 0 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card title="Model Bazında Satış">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[...sales.model].sort((a,b) => b.satis - a.satis)} layout="vertical" margin={{ left: 20, right: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="model" tick={{ fontSize: 12 }} width={40} />
                  <Tooltip />
                  <Bar dataKey="satis" name="Satış" radius={[0,4,4,0]}>
                    {sales.model.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    <LabelList dataKey="satis" position="right" style={{ fontSize: 11 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Model Pazar Payı (%)">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[...sales.model].sort((a,b) => b.pay - a.pay)} layout="vertical" margin={{ left: 20, right: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="model" tick={{ fontSize: 12 }} width={40} />
                  <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Bar dataKey="pay" name="Pay %" radius={[0,4,4,0]}>
                    {sales.model.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    <LabelList dataKey="pay" position="right" formatter={(v: number) => `${v.toFixed(1)}%`} style={{ fontSize: 11 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card title="Bayi Bazında Toplam Satış">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={[...sales.bayi].sort((a,b) => numSort(a.dealer, b.dealer))}
                margin={{ left: 0, right: 10, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="satis" name="Satış" fill="#3b82f6" radius={[4,4,0,0]}>
                  <LabelList dataKey="satis" position="top" style={{ fontSize: 10 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 1: Renk & Bayi */}
      {tab === 1 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card title="Renk Bazında Satış">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={[...sales.renk].sort((a,b) => b.satis - a.satis)} layout="vertical" margin={{ left: 20, right: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="renk" tick={{ fontSize: 11 }} width={65} />
                  <Tooltip />
                  <Bar dataKey="satis" name="Satış" radius={[0,4,4,0]}>
                    {sales.renk.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    <LabelList dataKey="satis" position="right" style={{ fontSize: 11 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Renk Pazar Payı (%)">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={[...sales.renk].sort((a,b) => b.pay - a.pay)} layout="vertical" margin={{ left: 20, right: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="renk" tick={{ fontSize: 11 }} width={65} />
                  <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Bar dataKey="pay" name="Pay %" radius={[0,4,4,0]}>
                    {sales.renk.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    <LabelList dataKey="pay" position="right" formatter={(v: number) => `${v.toFixed(1)}%`} style={{ fontSize: 11 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Top 3 colors table */}
          <Card title="Bayi Başına Top 3 Renk">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-3 py-2 text-xs font-medium text-slate-500">Bayi</th>
                    <th className="text-left px-3 py-2 text-xs font-medium text-slate-500">1. Renk</th>
                    <th className="text-right px-3 py-2 text-xs font-medium text-slate-500">Adet</th>
                    <th className="text-left px-3 py-2 text-xs font-medium text-slate-500">2. Renk</th>
                    <th className="text-right px-3 py-2 text-xs font-medium text-slate-500">Adet</th>
                    <th className="text-left px-3 py-2 text-xs font-medium text-slate-500">3. Renk</th>
                    <th className="text-right px-3 py-2 text-xs font-medium text-slate-500">Adet</th>
                  </tr>
                </thead>
                <tbody>
                  {[...sales.top3_renk].sort((a,b) => numSort(a.dealer, b.dealer)).map(row => (
                    <tr key={row.dealer} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-800">{row.dealer}</td>
                      <td className="px-3 py-2 text-slate-600">{row.renk1}</td>
                      <td className="px-3 py-2 text-right font-mono text-slate-700">{row.adet1}</td>
                      <td className="px-3 py-2 text-slate-600">{row.renk2}</td>
                      <td className="px-3 py-2 text-right font-mono text-slate-700">{row.adet2}</td>
                      <td className="px-3 py-2 text-slate-600">{row.renk3 || '-'}</td>
                      <td className="px-3 py-2 text-right font-mono text-slate-700">{row.adet3 || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Stacked bar: bayi × renk */}
          <Card title="Bayi × Renk Dağılımı (Stacked)">
            <ResponsiveContainer width="100%" height={420}>
              <BarChart data={stackedData} margin={{ left: 0, right: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ paddingTop: 16, fontSize: 11 }} />
                {allColors.map((c, i) => (
                  <Bar key={c} dataKey={c} stackId="a" fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 2: Aylık Trend */}
      {tab === 2 && (
        <Card title="Aylık Satış Trendi">
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={sales.aylik} margin={{ left: 0, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line dataKey="satis" name="Satış" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 6 }}>
                <LabelList dataKey="satis" position="top" style={{ fontSize: 10 }} />
              </Line>
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* TAB 3: Hedef Gerçekleşme */}
      {tab === 3 && (
        <div className="space-y-6">
          {/* KPI */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Toplam Hedef',    value: hedefRows.reduce((s,r) => s + r.hedef, 0).toLocaleString('tr') },
              { label: 'Toplam Gerçek',   value: hedefRows.reduce((s,r) => s + r.gercek, 0).toLocaleString('tr') },
              { label: 'Ort. Gerçekleşme',value: hedefRows.length ? `%${(hedefRows.reduce((s,r) => s + r.pct, 0) / hedefRows.length).toFixed(1)}` : '-' },
              { label: 'Yeşil Ay',        value: `${hedefRows.filter(r => r.pct >= 100).length} / ${hedefRows.length}` },
            ].map(k => (
              <div key={k.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
                <p className="text-xs text-slate-500 mb-1">{k.label}</p>
                <p className="text-xl font-bold text-slate-900">{k.value}</p>
              </div>
            ))}
          </div>

          <Card title="Hedef vs Gerçekleşme">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={hedefRows} margin={{ left: 0, right: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="period" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="hedef"  name="Hedef"       fill="#94a3b8" radius={[4,4,0,0]} />
                <Bar dataKey="gercek" name="Gerçekleşen" radius={[4,4,0,0]}>
                  {hedefRows.map((r, i) => <Cell key={i} fill={r.pct >= 100 ? '#22c55e' : '#ef4444'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Gerçekleşme Oranı (%)">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={hedefRows} margin={{ left: 0, right: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="period" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `%${v}`} />
                <Tooltip formatter={(v: number) => `%${v.toFixed(1)}`} />
                <ReferenceLine y={100} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: '%100', position: 'right', fontSize: 10 }} />
                <Bar dataKey="pct" name="Gerçekleşme %" radius={[4,4,0,0]}>
                  {hedefRows.map((r, i) => <Cell key={i} fill={r.pct >= 100 ? '#22c55e' : '#ef4444'} />)}
                  <LabelList dataKey="pct" position="top" formatter={(v: number) => `%${v.toFixed(0)}`} style={{ fontSize: 9 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* TAB 4: Rakip Karşılaştırma */}
      {tab === 4 && (
        <Card title="Rakip Marka Satış Karşılaştırması">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={rakipChart} margin={{ left: 0, right: 20, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {rakipMarkas.map((m, i) => (
                <Line
                  key={m}
                  dataKey={m}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  strokeWidth={m === 'Marka X' ? 3 : 1.5}
                  dot={false}
                  strokeDasharray={m === 'Marka X' ? undefined : '4 2'}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  )
}
