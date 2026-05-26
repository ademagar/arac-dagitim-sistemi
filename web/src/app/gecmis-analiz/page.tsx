'use client'

import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, ResponsiveContainer, Cell, LabelList,
  ReferenceLine,
} from 'recharts'
import { CHART_COLORS, numSort } from '@/lib/utils'

type YearKey = '2024' | '2025' | 'all'
type Tab = 'model' | 'renk' | 'trend' | 'hedef' | 'rakip'

interface SalesData {
  model: { model: string; satis: number; pay: number }[]
  renk:  { renk: string; satis: number; pay: number }[]
  bayi:  { dealer: string; satis: number }[]
  aylik: { period: string; satis: number; year_month: string }[]
  bayi_renk: { dealer: string; renk: string; n: number }[]
  top3_renk: { dealer: string; renk1: string; adet1: number; renk2: string; adet2: number; renk3: string; adet3: number }[]
}

interface HedefRow { period: string; hedef: number; gercek: number; pct: number }
interface HedefData { '2024': HedefRow[]; '2025': HedefRow[]; all: HedefRow[] }
interface RakipRow { marka: string; period: string; year_month: string; satis: number }

const YEAR_LABELS: Record<YearKey, string> = { '2024': '2024', '2025': '2025', 'all': 'Tümü (2024–2025)' }
const TABS: { key: Tab; label: string }[] = [
  { key: 'model',  label: 'Model & Versiyon' },
  { key: 'renk',   label: 'Renk & Bayi' },
  { key: 'trend',  label: 'Aylık Trend' },
  { key: 'hedef',  label: 'Hedef Gerçekleşme' },
  { key: 'rakip',  label: 'Rakip Karşılaştırma' },
]

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      {title && <h3 className="text-sm font-semibold text-slate-600 mb-4">{title}</h3>}
      {children}
    </div>
  )
}

function DataTable({ rows, cols }: { rows: Record<string, unknown>[]; cols: { key: string; label: string }[] }) {
  if (!rows.length) return <p className="text-slate-400 text-sm">Veri yok</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {cols.map(c => (
              <th key={c.key} className="text-left py-2 px-3 text-slate-500 font-medium whitespace-nowrap">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
              {cols.map(c => (
                <td key={c.key} className="py-2 px-3 text-slate-700 whitespace-nowrap">
                  {String(row[c.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function GecmisAnaliz() {
  const [year, setYear]       = useState<YearKey>('2025')
  const [tab, setTab]         = useState<Tab>('model')
  const [sales, setSales]     = useState<SalesData | null>(null)
  const [hedef, setHedef]     = useState<HedefData | null>(null)
  const [rakip, setRakip]     = useState<RakipRow[]>([])

  useEffect(() => {
    fetch(`/data/sales-${year}.json`).then(r => r.json()).then(setSales)
  }, [year])

  useEffect(() => {
    fetch('/data/hedef.json').then(r => r.json()).then(setHedef)
    fetch('/data/rakip.json').then(r => r.json()).then(setRakip)
  }, [])

  const hedefRows: HedefRow[] = hedef ? (year === 'all' ? hedef.all : hedef[year]) : []

  // Stacked bar: bayi × renk
  const dealerOrder = sales?.bayi.map(b => b.dealer) ?? []
  const allColors = [...new Set((sales?.bayi_renk ?? []).map(r => r.renk))].sort()
  const stackedData = dealerOrder.map(dealer => {
    const row: Record<string, unknown> = { dealer }
    allColors.forEach(color => {
      const found = sales?.bayi_renk.find(r => r.dealer === dealer && r.renk === color)
      row[color] = found?.n ?? 0
    })
    return row
  })

  // Rakip: filter by year
  const rakipFiltered = year === 'all'
    ? rakip
    : rakip.filter(r => r.year_month.startsWith(year))
  const rakipByMarka = [...new Set(rakipFiltered.map(r => r.marka))]
  const rakipPeriods = [...new Set(rakipFiltered.map(r => r.period))].sort()
  const rakipChartData = rakipPeriods.map(period => {
    const row: Record<string, unknown> = { period }
    rakipByMarka.forEach(marka => {
      const found = rakipFiltered.find(r => r.period === period && r.marka === marka)
      row[marka] = found?.satis ?? 0
    })
    return row
  })
  const rakipTotals = rakipByMarka.map(marka => ({
    marka,
    toplam: rakipFiltered.filter(r => r.marka === marka).reduce((s, r) => s + r.satis, 0),
  })).sort((a, b) => b.toplam - a.toplam)

  return (
    <div>
      {/* Başlık */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Geçmiş Satış Analizi</h1>
        <p className="text-slate-500 text-sm mt-1">2024 ve 2025 yıllarına ait model, renk ve bayi bazlı satış verileri</p>
      </div>

      {/* Dönem seçici */}
      <div className="flex gap-2 mb-6">
        {(Object.keys(YEAR_LABELS) as YearKey[]).map(y => (
          <button
            key={y}
            onClick={() => setYear(y)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              year === y ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:border-blue-300'
            }`}
          >
            {YEAR_LABELS[y]}
          </button>
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ---- Tab 1: Model & Versiyon ---- */}
      {tab === 'model' && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <Card title="Model Bazında Satışlar">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={sales?.model ?? []} layout="vertical" margin={{ left: 10, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="model" tick={{ fontSize: 12 }} width={50} />
                <Tooltip formatter={(v: number) => [v.toLocaleString('tr'), 'Satış']} />
                <Bar dataKey="satis" fill="#3B82F6" radius={[0,4,4,0]}>
                  <LabelList dataKey="satis" position="right" style={{ fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Model Satış Payı (%)">
            <DataTable
              rows={(sales?.model ?? []).map(r => ({
                model: r.model,
                satis: r.satis.toLocaleString('tr'),
                pay: `%${r.pay.toFixed(1)}`,
              }))}
              cols={[
                { key: 'model', label: 'Model' },
                { key: 'satis', label: 'Satış' },
                { key: 'pay',   label: 'Pay' },
              ]}
            />
          </Card>

          <Card title="Bayi Toplam Satışları">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={sales?.bayi ?? []} layout="vertical" margin={{ left: 10, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="dealer" tick={{ fontSize: 11 }} width={72} />
                <Tooltip formatter={(v: number) => [v.toLocaleString('tr'), 'Satış']} />
                <Bar dataKey="satis" fill="#10B981" radius={[0,4,4,0]}>
                  <LabelList dataKey="satis" position="right" style={{ fontSize: 10 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Bayi Toplam Satış Tablosu">
            <DataTable
              rows={(sales?.bayi ?? []).map(r => ({ dealer: r.dealer, satis: r.satis.toLocaleString('tr') }))}
              cols={[
                { key: 'dealer', label: 'Bayi' },
                { key: 'satis',  label: 'Toplam Satış' },
              ]}
            />
          </Card>
        </div>
      )}

      {/* ---- Tab 2: Renk & Bayi ---- */}
      {tab === 'renk' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <Card title="Renk Dağılımı">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={sales?.renk ?? []} layout="vertical" margin={{ left: 10, right: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="renk" tick={{ fontSize: 11 }} width={65} />
                  <Tooltip formatter={(v: number) => [v.toLocaleString('tr'), 'Satış']} />
                  <Bar dataKey="satis" radius={[0,4,4,0]}>
                    {(sales?.renk ?? []).map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                    <LabelList dataKey="satis" position="right" style={{ fontSize: 10 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Renk Satış Tablosu">
              <DataTable
                rows={(sales?.renk ?? []).map(r => ({
                  renk: r.renk,
                  satis: r.satis.toLocaleString('tr'),
                  pay: `%${r.pay.toFixed(1)}`,
                }))}
                cols={[
                  { key: 'renk', label: 'Renk' },
                  { key: 'satis', label: 'Satış' },
                  { key: 'pay',   label: 'Pay' },
                ]}
              />
            </Card>
          </div>

          <Card title="Bayi Başına Top 3 Renk">
            <DataTable
              rows={sales?.top3_renk ?? []}
              cols={[
                { key: 'dealer', label: 'Bayi' },
                { key: 'renk1',  label: '1. Renk' },
                { key: 'adet1',  label: 'Adet' },
                { key: 'renk2',  label: '2. Renk' },
                { key: 'adet2',  label: 'Adet' },
                { key: 'renk3',  label: '3. Renk' },
                { key: 'adet3',  label: 'Adet' },
              ]}
            />
          </Card>

          <Card title={`Bayi Bazında Renk Dağılımı (${YEAR_LABELS[year]})`}>
            <ResponsiveContainer width="100%" height={480}>
              <BarChart data={stackedData} margin={{ bottom: 80, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-40} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ paddingTop: 12, fontSize: 11 }} />
                {allColors.map((color, i) => (
                  <Bar key={color} dataKey={color} stackId="a" fill={CHART_COLORS[i % CHART_COLORS.length]}>
                    <LabelList dataKey={color} position="inside" style={{ fontSize: 9, fill: '#fff' }}
                      formatter={(v: number) => (v > 0 ? v : '')} />
                  </Bar>
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* ---- Tab 3: Aylık Trend ---- */}
      {tab === 'trend' && (
        <div className="space-y-5">
          <Card title="Aylık Satış Trendi">
            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={sales?.aylik ?? []} margin={{ right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={55} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [v.toLocaleString('tr'), 'Satış']} />
                <Line type="monotone" dataKey="satis" stroke="#3B82F6" strokeWidth={2.5}
                  dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Aylık Trend Tablosu">
            <DataTable
              rows={(sales?.aylik ?? []).map(r => ({ period: r.period, satis: r.satis.toLocaleString('tr') }))}
              cols={[
                { key: 'period', label: 'Dönem' },
                { key: 'satis',  label: 'Satış Adedi' },
              ]}
            />
          </Card>
        </div>
      )}

      {/* ---- Tab 4: Hedef Gerçekleşme ---- */}
      {tab === 'hedef' && (
        <div className="space-y-5">
          {/* Kanal filtre badge */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Kanal filtresi:</span>
            <span className="bg-blue-600 text-white text-xs px-3 py-1 rounded-full font-medium">✓ B2C</span>
            <span className="bg-slate-100 text-slate-400 text-xs px-3 py-1 rounded-full line-through">B2B</span>
            <span className="bg-slate-100 text-slate-400 text-xs px-3 py-1 rounded-full line-through">B2B+B2C</span>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <Card title="B2C Aylık Hedef">
              <DataTable
                rows={hedefRows.map(r => ({ period: r.period, hedef: r.hedef.toLocaleString('tr') }))}
                cols={[{ key: 'period', label: 'Dönem' }, { key: 'hedef', label: 'Hedef' }]}
              />
            </Card>
            <Card title="B2C Aylık Gerçekleşen">
              <DataTable
                rows={hedefRows.map(r => ({ period: r.period, gercek: r.gercek.toLocaleString('tr') }))}
                cols={[{ key: 'period', label: 'Dönem' }, { key: 'gercek', label: 'Gerçekleşen' }]}
              />
            </Card>
          </div>

          <Card title="B2C Aylık Gerçekleşme Oranı (%)">
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={hedefRows} margin={{ right: 20, top: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={55} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                <Tooltip formatter={(v: number) => [`%${v}`, 'Gerçekleşme']} />
                <ReferenceLine y={100} stroke="#3B82F6" strokeDasharray="5 3" strokeWidth={2}
                  label={{ value: '%100 Hedef', position: 'right', fontSize: 11, fill: '#3B82F6' }} />
                <Bar dataKey="pct" radius={[4,4,0,0]} maxBarSize={48}>
                  {hedefRows.map((r, i) => (
                    <Cell key={i} fill={r.pct >= 100 ? '#22C55E' : '#EF4444'} />
                  ))}
                  <LabelList dataKey="pct" position="top" formatter={(v: number) => `%${v}`}
                    style={{ fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* ---- Tab 5: Rakip ---- */}
      {tab === 'rakip' && (
        <div className="space-y-5">
          <Card title={`Rakip Marka Aylık Satışları (${YEAR_LABELS[year]})`}>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={rakipChartData} margin={{ right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={55} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {rakipByMarka.map((marka, i) => (
                  <Line key={marka} type="monotone" dataKey={marka}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title={`${YEAR_LABELS[year]} Yıllık Toplam Satış Karşılaştırması`}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={rakipTotals} layout="vertical" margin={{ left: 10, right: 60 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="marka" tick={{ fontSize: 11 }} width={90} />
                <Tooltip formatter={(v: number) => [v.toLocaleString('tr'), 'Satış']} />
                <Bar dataKey="toplam" fill="#3B82F6" radius={[0,4,4,0]}>
                  <LabelList dataKey="toplam" position="right" style={{ fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  )
}
