import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

// ---------------------------------------------------------------------------
// Tipler
// ---------------------------------------------------------------------------

interface AralikOzet {
  toplam_tahmin: number
  toplam_gercek: number
  mape: number
  mae: number
  rmse: number
  bayi_mape: number | null
  yontem: string
}

interface BayiTahmin {
  dealer: string
  tahmin: number
  gercek: number
  hata_pct: number | null
  model_mix: Record<string, number>
}

interface AylikTrend {
  ym: string
  gercek: number
  tahmin: number | null
}

interface Metodoloji {
  baslik: string
  aciklama: string
}

interface AralikTahmin {
  ozet: AralikOzet
  bayi_tahmin: BayiTahmin[]
  aylik_trend: AylikTrend[]
  metodoloji: Metodoloji[]
}

interface Plan2026Ozet {
  yillik_hedef: number
  ocak_hedef: number
  lansman_ay: number
  lansman_boost: number
  toplam_kontrol: number
}

interface AylikPlan {
  ay: number
  ay_adi: string
  hedef: number
  si: number
  lansman_boost: number
  pay_pct: number
}

interface OcakBayiDagilim {
  dealer: string
  adet: number
  pay_pct: number
  model_mix: Record<string, number>
  gercekci_mi: 'Yüksek' | 'Orta' | 'Düşük'
  jan26_hedef: number
  perf_skoru: number
}

interface Plan2026 {
  ozet: Plan2026Ozet
  aylik: AylikPlan[]
  ocak_bayi_dagilim: OcakBayiDagilim[]
  metodoloji: Metodoloji[]
}

interface TahminData {
  aralik_tahmin: AralikTahmin
  plan_2026: Plan2026
}

// ---------------------------------------------------------------------------
// Yardımcı bileşenler (Mevsimsellik.tsx ile aynı pattern)
// ---------------------------------------------------------------------------

function TabBar({ tabs, active, onChange }: {
  tabs: string[]
  active: number
  onChange: (i: number) => void
}) {
  return (
    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg mb-6 w-fit flex-wrap">
      {tabs.map((t, i) => (
        <button
          key={t}
          onClick={() => onChange(i)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            active === i
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
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

function MetricCard({
  label, value, sub, colorClass,
}: {
  label: string
  value: string
  sub?: string
  colorClass?: string
}) {
  return (
    <div className={`rounded-xl border p-4 ${colorClass ?? 'bg-white border-slate-200'}`}>
      <p className="text-xs font-medium text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function ModelChips({ mix }: { mix: Record<string, number> }) {
  const MODEL_COLORS: Record<string, string> = {
    A1: 'bg-blue-100 text-blue-700',
    A2: 'bg-green-100 text-green-700',
    A3: 'bg-amber-100 text-amber-700',
    B1: 'bg-purple-100 text-purple-700',
    B2: 'bg-pink-100 text-pink-700',
    C1: 'bg-cyan-100 text-cyan-700',
    D1: 'bg-red-100 text-red-700',
  }
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(mix)
        .sort((a, b) => b[1] - a[1])
        .filter(([, v]) => v > 0.03)
        .map(([model, pct]) => (
          <span
            key={model}
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${MODEL_COLORS[model] ?? 'bg-slate-100 text-slate-600'}`}
          >
            {model} {(pct * 100).toFixed(0)}%
          </span>
        ))}
    </div>
  )
}

function GercekcilikBadge({ seviye }: { seviye: string }) {
  const map: Record<string, string> = {
    'Yüksek': 'bg-green-100 text-green-700',
    'Orta': 'bg-amber-100 text-amber-700',
    'Düşük': 'bg-red-100 text-red-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${map[seviye] ?? 'bg-slate-100 text-slate-600'}`}>
      {seviye}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Sekme 1: Aralık 2025 Tahmini
// ---------------------------------------------------------------------------

function AralikTab({ data }: { data: AralikTahmin }) {
  const [sortField, setSortField] = useState<'hata_pct' | 'gercek' | 'tahmin'>('hata_pct')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const { ozet, bayi_tahmin, aylik_trend, metodoloji } = data

  // Sıralanmış bayi listesi
  const sortedBayiler = [...bayi_tahmin].sort((a, b) => {
    const aVal = sortField === 'hata_pct' ? Math.abs(a.hata_pct ?? 0) : a[sortField]
    const bVal = sortField === 'hata_pct' ? Math.abs(b.hata_pct ?? 0) : b[sortField]
    return sortDir === 'asc' ? aVal - bVal : bVal - aVal
  })

  function toggleSort(field: typeof sortField) {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  // Grafik verisi: gerçek çizgi + son nokta olarak tahmin
  const chartData = aylik_trend.map(r => ({
    ym: r.ym.replace('-', '-'),
    gercek: r.gercek,
    tahmin: r.tahmin,
  }))

  // Hata yönü
  const hataYonu = ozet.toplam_tahmin > ozet.toplam_gercek ? 'fazla tahmin' : 'düşük tahmin'
  const mapeRenk = ozet.mape < 10 ? 'text-green-600' : ozet.mape < 20 ? 'text-amber-600' : 'text-red-600'

  return (
    <div className="space-y-6">
      {/* Özet kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard
          label="Tahmin"
          value={ozet.toplam_tahmin.toLocaleString('tr')}
          sub="araç"
          colorClass="bg-blue-50 border-blue-200"
        />
        <MetricCard
          label="Gerçek"
          value={ozet.toplam_gercek.toLocaleString('tr')}
          sub="araç (Dec 2025)"
          colorClass="bg-slate-50 border-slate-200"
        />
        <MetricCard
          label="MAPE"
          value={`${ozet.mape.toFixed(1)}%`}
          sub={hataYonu}
          colorClass={ozet.mape < 10 ? 'bg-green-50 border-green-200' : ozet.mape < 20 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}
        />
        <MetricCard
          label="MAE"
          value={ozet.mae.toFixed(0)}
          sub="araç mutlak hata"
          colorClass="bg-white border-slate-200"
        />
        <MetricCard
          label="Bayi MAPE"
          value={ozet.bayi_mape != null ? `${ozet.bayi_mape.toFixed(1)}%` : '—'}
          sub="bayi bazında ort."
          colorClass="bg-white border-slate-200"
        />
      </div>

      {/* Metodoloji kutusu */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
        <p className="text-sm font-semibold text-blue-800 mb-2">Tahmin Metodolojisi</p>
        <ul className="space-y-1">
          {metodoloji.map(m => (
            <li key={m.baslik} className="text-xs text-blue-700">
              <span className="font-medium">{m.baslik}:</span> {m.aciklama}
            </li>
          ))}
        </ul>
        <p className={`text-xs font-mono mt-3 ${mapeRenk}`}>
          {ozet.yontem}
        </p>
      </div>

      {/* Aylık trend grafiği */}
      <Card title="Aylık Satış Trendi (Ocak 2024 – Aralık 2025)">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ left: 0, right: 20, top: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="ym"
              tick={{ fontSize: 10 }}
              tickFormatter={v => v.slice(2)}
              interval={1}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v: number, name: string) => [
                v?.toLocaleString('tr'),
                name === 'gercek' ? 'Gerçek Satış' : 'Tahmin (Dec 2025)',
              ]}
            />
            <Legend
              formatter={v => v === 'gercek' ? 'Gerçek Satış' : 'Tahmin (Aralık 2025)'}
            />
            <ReferenceLine x="2025-12" stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Tahmin', fontSize: 10, fill: '#ef4444' }} />
            <Line
              dataKey="gercek"
              name="gercek"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3, fill: '#3b82f6' }}
              connectNulls={false}
            />
            <Line
              dataKey="tahmin"
              name="tahmin"
              stroke="#ef4444"
              strokeWidth={2.5}
              strokeDasharray="6 3"
              dot={{ r: 6, fill: '#ef4444', strokeWidth: 2 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-slate-400 text-center mt-1">
          Kırmızı nokta = Aralık 2025 tahmini · Mavi çizgi = gerçek satışlar
        </p>
      </Card>

      {/* Bayi tahmin tablosu */}
      <Card title="Bayi Bazında Tahmin vs Gerçek">
        <p className="text-xs text-slate-500 mb-3">
          Sütun başlıklarına tıklayarak sıralayabilirsiniz.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-2 font-medium text-slate-500">Bayi</th>
                <th
                  className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('tahmin')}
                >
                  Tahmin {sortField === 'tahmin' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th
                  className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('gercek')}
                >
                  Gerçek {sortField === 'gercek' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th
                  className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('hata_pct')}
                >
                  Hata% {sortField === 'hata_pct' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th className="text-left py-2 px-3 font-medium text-slate-500">Model Karışımı</th>
              </tr>
            </thead>
            <tbody>
              {sortedBayiler.map(row => {
                const hataAbs = row.hata_pct != null ? Math.abs(row.hata_pct) : null
                const hataRenk =
                  hataAbs == null ? 'text-slate-400'
                  : hataAbs < 10 ? 'text-green-600'
                  : hataAbs < 20 ? 'text-amber-600'
                  : 'text-red-600'
                const hataBg =
                  hataAbs == null ? ''
                  : hataAbs < 10 ? 'bg-green-50'
                  : hataAbs < 20 ? 'bg-amber-50'
                  : 'bg-red-50'
                return (
                  <tr key={row.dealer} className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${hataBg}`}>
                    <td className="py-2 px-2 font-medium text-slate-700">{row.dealer}</td>
                    <td className="py-2 px-2 text-right font-mono text-slate-700">{row.tahmin}</td>
                    <td className="py-2 px-2 text-right font-mono text-slate-700">{row.gercek}</td>
                    <td className={`py-2 px-2 text-right font-mono font-semibold ${hataRenk}`}>
                      {row.hata_pct != null ? `${row.hata_pct > 0 ? '+' : ''}${row.hata_pct.toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <ModelChips mix={row.model_mix} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-50">
                <td className="py-2 px-2 font-bold text-slate-800">TOPLAM</td>
                <td className="py-2 px-2 text-right font-bold font-mono text-blue-700">
                  {bayi_tahmin.reduce((s, r) => s + r.tahmin, 0)}
                </td>
                <td className="py-2 px-2 text-right font-bold font-mono text-slate-800">
                  {bayi_tahmin.reduce((s, r) => s + r.gercek, 0)}
                </td>
                <td className="py-2 px-2 text-right font-semibold text-slate-500">—</td>
                <td className="py-2 px-3 text-xs text-slate-400">son 12 ay mix</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Renk: yeşil &lt;10% · sarı 10-20% · kırmızı &gt;20% mutlak hata
        </p>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sekme 2: 2026 Yıllık Plan
// ---------------------------------------------------------------------------

function Plan2026Tab({ data }: { data: Plan2026 }) {
  const { ozet, aylik, ocak_bayi_dagilim, metodoloji } = data

  const LANSMAN_AY = ozet.lansman_ay
  const barRenk = (ay: number) =>
    ay === LANSMAN_AY ? '#22c55e' : ay >= LANSMAN_AY ? '#3b82f6' : '#94a3b8'

  const ocakToplam = ocak_bayi_dagilim.reduce((s, r) => s + r.adet, 0)

  return (
    <div className="space-y-6">
      {/* Özet kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Yıllık Hedef"
          value={ozet.yillik_hedef.toLocaleString('tr')}
          sub="araç (2026)"
          colorClass="bg-blue-50 border-blue-200"
        />
        <MetricCard
          label="Ocak 2026"
          value={ozet.ocak_hedef.toLocaleString('tr')}
          sub="araç (sabit)"
          colorClass="bg-slate-50 border-slate-200"
        />
        <MetricCard
          label="Lansman Ayı"
          value="Mart 2026"
          sub={`×${ozet.lansman_boost} boost`}
          colorClass="bg-green-50 border-green-200"
        />
        <MetricCard
          label="Doğrulama"
          value={ozet.toplam_kontrol.toLocaleString('tr')}
          sub={ozet.toplam_kontrol === ozet.yillik_hedef ? '= hedef ✓' : '≠ hedef!'}
          colorClass={ozet.toplam_kontrol === ozet.yillik_hedef ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}
        />
      </div>

      {/* Aylık hedef bar chart */}
      <Card title="2026 Aylık Araç Dağıtım Hedefi">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={aylik} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="ay_adi" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v: number) => [`${v.toLocaleString('tr')} araç`, 'Hedef']}
              labelFormatter={label => `${label} 2026`}
            />
            <ReferenceLine y={ozet.yillik_hedef / 12} stroke="#94a3b8" strokeDasharray="4 4"
              label={{ value: 'Aylık ort.', fontSize: 10, fill: '#94a3b8' }} />
            <Bar dataKey="hedef" name="Hedef" radius={[4, 4, 0, 0]}>
              {aylik.map(row => (
                <Cell key={row.ay} fill={barRenk(row.ay)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 justify-center text-xs text-slate-500">
          <span><span className="inline-block w-3 h-3 rounded bg-slate-300 mr-1" />Ocak–Şubat (lansman öncesi)</span>
          <span><span className="inline-block w-3 h-3 rounded bg-green-500 mr-1" />Mart (lansman)</span>
          <span><span className="inline-block w-3 h-3 rounded bg-blue-500 mr-1" />Nisan–Aralık</span>
        </div>
      </Card>

      {/* Lansman açıklama kutusu */}
      <div className="bg-green-50 rounded-xl border border-green-200 p-4">
        <p className="text-sm font-semibold text-green-800 mb-2">
          Mart 2026 Lansman Etkisi
        </p>
        <p className="text-xs text-green-700 mb-1">
          Final SI (Mart) = {aylik.find(r => r.ay === LANSMAN_AY)?.si.toFixed(3)} × Lansman boost ({ozet.lansman_boost}x) ile
          toplam çarpan = {((aylik.find(r => r.ay === LANSMAN_AY)?.si ?? 1) * ozet.lansman_boost).toFixed(3)}
        </p>
        <p className="text-xs text-green-700">
          Mart ayı hedefi: <strong>{aylik.find(r => r.ay === LANSMAN_AY)?.hedef.toLocaleString('tr')} araç</strong>
          {' '}({aylik.find(r => r.ay === LANSMAN_AY)?.pay_pct.toFixed(1)}% yıllık hedef)
        </p>
        <ul className="mt-2 space-y-1">
          {metodoloji.map(m => (
            <li key={m.baslik} className="text-xs text-green-700">
              <span className="font-medium">{m.baslik}:</span> {m.aciklama}
            </li>
          ))}
        </ul>
      </div>

      {/* Ocak 2026 Bayi Dağılımı */}
      <Card title={`Ocak 2026 Bayi Dağılımı (Toplam: ${ocakToplam} araç)`}>
        <div className="flex gap-4 mb-3 text-xs text-slate-500">
          <span>Ağırlık: <strong>50%</strong> son 12 ay satış payı</span>
          <span>+ <strong>30%</strong> Ocak 2026 hedef payı</span>
          <span>+ <strong>20%</strong> performans skoru</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-2 font-medium text-slate-500">Bayi</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Tahmin Adet</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Pay%</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Jan26 Hedef</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Perf. Sk.</th>
                <th className="text-center py-2 px-2 font-medium text-slate-500">Güven</th>
                <th className="text-left py-2 px-3 font-medium text-slate-500">Model Karışımı</th>
              </tr>
            </thead>
            <tbody>
              {ocak_bayi_dagilim.map(row => (
                <tr key={row.dealer} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 px-2 font-medium text-slate-700">{row.dealer}</td>
                  <td className="py-2 px-2 text-right font-mono font-semibold text-blue-700">{row.adet}</td>
                  <td className="py-2 px-2 text-right font-mono text-slate-600">
                    {row.pay_pct.toFixed(1)}%
                    <div className="w-full bg-slate-100 rounded-full h-1 mt-0.5">
                      <div
                        className="h-1 rounded-full bg-blue-400"
                        style={{ width: `${Math.min(100, row.pay_pct * 4)}%` }}
                      />
                    </div>
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-slate-500">{row.jan26_hedef}</td>
                  <td className="py-2 px-2 text-right font-mono text-slate-500">
                    {(row.perf_skoru * 100).toFixed(0)}%
                  </td>
                  <td className="py-2 px-2 text-center">
                    <GercekcilikBadge seviye={row.gercekci_mi} />
                  </td>
                  <td className="py-2 px-3">
                    <ModelChips mix={row.model_mix} />
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-50">
                <td className="py-2 px-2 font-bold text-slate-800">TOPLAM</td>
                <td className="py-2 px-2 text-right font-bold font-mono text-blue-700">
                  {ocakToplam}
                </td>
                <td className="py-2 px-2 text-right font-mono font-bold text-slate-600">100%</td>
                <td className="py-2 px-2 text-right font-mono text-slate-500">
                  {ocak_bayi_dagilim.reduce((s, r) => s + r.jan26_hedef, 0)}
                </td>
                <td colSpan={3} className="py-2 px-2 text-xs text-slate-400 text-center">
                  {ocakToplam === ozet.ocak_hedef
                    ? `✓ Toplam = ${ozet.ocak_hedef} araç`
                    : `Toplam = ${ocakToplam} ≠ ${ozet.ocak_hedef}!`}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Güven: Yüksek = tahmin/hedef 0.8–1.25 · Orta = 0.6–1.5 · Düşük = dışında
        </p>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------

export default function Tahmin() {
  const [data, setData] = useState<TahminData | null>(null)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    fetch(`${base}data/tahmin.json`)
      .then(r => r.json())
      .then(setData)
      .catch(err => console.error('tahmin.json yüklenemedi:', err))
  }, [])

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Yükleniyor…
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Tahmin & Plan</h1>
        <p className="text-slate-500 text-sm mt-1">
          Aralık 2025 geriye dönük tahmin doğrulaması ve 2026 yıllık dağıtım planı
        </p>
      </div>

      <TabBar
        tabs={['Aralık 2025 Tahmini', '2026 Yıllık Plan']}
        active={tab}
        onChange={setTab}
      />

      {tab === 0 && <AralikTab data={data.aralik_tahmin} />}
      {tab === 1 && <Plan2026Tab data={data.plan_2026} />}
    </div>
  )
}
