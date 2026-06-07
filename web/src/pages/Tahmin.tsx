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

interface TierOzet {
  tier: 'A' | 'B' | 'C'
  aciklama: string
  tahmin: number
  gercek: number
  mape: number | null
  si: number
  trend: number
  son12_ort: number
}

interface BayiTahmin {
  dealer: string
  tier: 'A' | 'B' | 'C'
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
  tier_ozet: TierOzet[]
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
  tier: 'A' | 'B' | 'C'
  adet: number
  pay_pct: number
  model_mix: Record<string, number>
  gercekci_mi: 'Yüksek' | 'Orta' | 'Düşük'
  jan26_hedef: number
  perf_skoru: number
}

interface Senaryo {
  ozet: Plan2026Ozet
  aylik: AylikPlan[]
  ocak_bayi_dagilim: OcakBayiDagilim[]
}

interface Plan2026 {
  senaryo_8500: Senaryo
  senaryo_10000: Senaryo
  metodoloji: Metodoloji[]
}

interface TahminData {
  aralik_tahmin: AralikTahmin
  plan_2026: Plan2026
}

// ---------------------------------------------------------------------------
// Yardımcı bileşenler
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
  label: string; value: string; sub?: string; colorClass?: string
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
    A1: 'bg-blue-100 text-blue-700', A2: 'bg-green-100 text-green-700',
    A3: 'bg-amber-100 text-amber-700', B1: 'bg-purple-100 text-purple-700',
    B2: 'bg-pink-100 text-pink-700', C1: 'bg-cyan-100 text-cyan-700',
    D1: 'bg-red-100 text-red-700',
  }
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(mix)
        .sort((a, b) => b[1] - a[1])
        .filter(([, v]) => v > 0.03)
        .map(([model, pct]) => (
          <span key={model}
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${MODEL_COLORS[model] ?? 'bg-slate-100 text-slate-600'}`}
          >
            {model} {(pct * 100).toFixed(0)}%
          </span>
        ))}
    </div>
  )
}

function TierBadge({ tier }: { tier: 'A' | 'B' | 'C' }) {
  const TIER_STYLE: Record<string, string> = {
    A: 'bg-blue-600 text-white',
    B: 'bg-emerald-600 text-white',
    C: 'bg-slate-500 text-white',
  }
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-bold tracking-wide ${TIER_STYLE[tier]}`}>
      {tier}
    </span>
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
// Sekme 1: Aralık 2025 Tier Bazlı Tahmini
// ---------------------------------------------------------------------------

const TIER_ACIKLAMA: Record<string, string> = {
  A: 'Marmara + Ege + İç Anadolu',
  B: 'Akdeniz',
  C: 'Güneydoğu + Karadeniz',
}
const TIER_BG: Record<string, string> = {
  A: 'bg-blue-50 border-blue-200',
  B: 'bg-emerald-50 border-emerald-200',
  C: 'bg-slate-50 border-slate-200',
}
const TIER_TEXT: Record<string, string> = {
  A: 'text-blue-700',
  B: 'text-emerald-700',
  C: 'text-slate-700',
}

function AralikTab({ data }: { data: AralikTahmin }) {
  const [sortField, setSortField] = useState<'hata_pct' | 'gercek' | 'tahmin'>('hata_pct')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [filterTier, setFilterTier] = useState<'Tümü' | 'A' | 'B' | 'C'>('Tümü')

  const { ozet, tier_ozet, bayi_tahmin, aylik_trend, metodoloji } = data

  const filteredBayiler = bayi_tahmin.filter(
    r => filterTier === 'Tümü' || r.tier === filterTier,
  )

  const sortedBayiler = [...filteredBayiler].sort((a, b) => {
    const aVal = sortField === 'hata_pct' ? Math.abs(a.hata_pct ?? 0) : a[sortField]
    const bVal = sortField === 'hata_pct' ? Math.abs(b.hata_pct ?? 0) : b[sortField]
    return sortDir === 'asc' ? aVal - bVal : bVal - aVal
  })

  function toggleSort(field: typeof sortField) {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('asc') }
  }

  const chartData = aylik_trend.map(r => ({ ym: r.ym, gercek: r.gercek, tahmin: r.tahmin }))
  const hataYonu = ozet.toplam_tahmin > ozet.toplam_gercek ? 'fazla tahmin' : 'düşük tahmin'

  return (
    <div className="space-y-6">
      {/* Özet metrik kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Tahmin" value={ozet.toplam_tahmin.toLocaleString('tr')} sub="araç"
          colorClass="bg-blue-50 border-blue-200" />
        <MetricCard label="Gerçek" value={ozet.toplam_gercek.toLocaleString('tr')} sub="araç (Dec 2025)"
          colorClass="bg-slate-50 border-slate-200" />
        <MetricCard label="MAPE" value={`${ozet.mape.toFixed(1)}%`} sub={hataYonu}
          colorClass={ozet.mape < 10 ? 'bg-green-50 border-green-200' : ozet.mape < 20 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'} />
        <MetricCard label="MAE" value={ozet.mae.toFixed(0)} sub="araç mutlak hata"
          colorClass="bg-white border-slate-200" />
        <MetricCard label="Bayi MAPE" value={ozet.bayi_mape != null ? `${ozet.bayi_mape.toFixed(1)}%` : '—'}
          sub="bayi bazında ort." colorClass="bg-white border-slate-200" />
      </div>

      {/* Tier bazlı özet */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
          A / B / C Tier Bazlı Tahmin Doğrulaması
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {tier_ozet.map(t => (
            <div key={t.tier} className={`rounded-xl border p-4 ${TIER_BG[t.tier]}`}>
              <div className="flex items-center gap-2 mb-3">
                <TierBadge tier={t.tier} />
                <span className={`text-xs font-medium ${TIER_TEXT[t.tier]}`}>{t.aciklama}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-xs text-slate-400">Tahmin</p>
                  <p className={`text-xl font-bold ${TIER_TEXT[t.tier]}`}>{t.tahmin}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Gerçek</p>
                  <p className="text-xl font-bold text-slate-800">{t.gercek}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">MAPE</p>
                  <p className={`text-xl font-bold ${
                    t.mape == null ? 'text-slate-400'
                    : t.mape < 10 ? 'text-green-600'
                    : t.mape < 20 ? 'text-amber-600' : 'text-red-600'
                  }`}>
                    {t.mape != null ? `${t.mape.toFixed(1)}%` : '—'}
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-200 grid grid-cols-3 gap-1 text-center">
                <div>
                  <p className="text-xs text-slate-400">SI</p>
                  <p className="text-xs font-mono text-slate-600">{t.si.toFixed(3)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Trend</p>
                  <p className="text-xs font-mono text-slate-600">{t.trend.toFixed(3)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Son12 Ort.</p>
                  <p className="text-xs font-mono text-slate-600">{t.son12_ort.toFixed(0)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metodoloji kutusu */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
        <p className="text-sm font-semibold text-blue-800 mb-2">Tahmin Metodolojisi — Tier Bazlı Yaklaşım</p>
        <ul className="space-y-1">
          {metodoloji.map(m => (
            <li key={m.baslik} className="text-xs text-blue-700">
              <span className="font-medium">{m.baslik}:</span> {m.aciklama}
            </li>
          ))}
        </ul>
        <p className="text-xs font-mono mt-3 text-blue-600 break-words">{ozet.yontem}</p>
      </div>

      {/* Aylık trend grafiği */}
      <Card title="Aylık Satış Trendi (Ocak 2024 – Aralık 2025)">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ left: 0, right: 20, top: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="ym" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(2)} interval={1} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v: number, name: string) => [
                v?.toLocaleString('tr'),
                name === 'gercek' ? 'Gerçek Satış' : 'Tahmin (Dec 2025)',
              ]}
            />
            <Legend formatter={v => v === 'gercek' ? 'Gerçek Satış' : 'Tahmin (Aralık 2025)'} />
            <ReferenceLine x="2025-12" stroke="#ef4444" strokeDasharray="4 4"
              label={{ value: 'Tahmin', fontSize: 10, fill: '#ef4444' }} />
            <Line dataKey="gercek" name="gercek" stroke="#3b82f6" strokeWidth={2}
              dot={{ r: 3, fill: '#3b82f6' }} connectNulls={false} />
            <Line dataKey="tahmin" name="tahmin" stroke="#ef4444" strokeWidth={2.5}
              strokeDasharray="6 3" dot={{ r: 6, fill: '#ef4444', strokeWidth: 2 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-slate-400 text-center mt-1">
          Kırmızı nokta = Aralık 2025 tahmini · Mavi çizgi = gerçek satışlar
        </p>
      </Card>

      {/* Bayi tahmin tablosu */}
      <Card title="Bayi Bazında Tahmin vs Gerçek">
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <p className="text-xs text-slate-500">Sütun başlıklarına tıklayarak sıralayabilirsiniz.</p>
          <div className="flex gap-1 ml-auto">
            {(['Tümü', 'A', 'B', 'C'] as const).map(t => (
              <button key={t} onClick={() => setFilterTier(t)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  filterTier === t
                    ? 'bg-slate-800 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {t === 'Tümü' ? 'Tümü' : `Tier ${t}`}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-2 font-medium text-slate-500">Bayi</th>
                <th className="text-center py-2 px-2 font-medium text-slate-500">Tier</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('tahmin')}>
                  Tahmin {sortField === 'tahmin' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('gercek')}>
                  Gerçek {sortField === 'gercek' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th className="text-right py-2 px-2 font-medium text-slate-500 cursor-pointer hover:text-slate-800 select-none"
                  onClick={() => toggleSort('hata_pct')}>
                  Hata% {sortField === 'hata_pct' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th className="text-left py-2 px-3 font-medium text-slate-500">Model Karışımı</th>
              </tr>
            </thead>
            <tbody>
              {sortedBayiler.map(row => {
                const hataAbs = row.hata_pct != null ? Math.abs(row.hata_pct) : null
                const hataRenk = hataAbs == null ? 'text-slate-400' : hataAbs < 10 ? 'text-green-600' : hataAbs < 20 ? 'text-amber-600' : 'text-red-600'
                const hataBg = hataAbs == null ? '' : hataAbs < 10 ? 'bg-green-50' : hataAbs < 20 ? 'bg-amber-50' : 'bg-red-50'
                return (
                  <tr key={row.dealer} className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${hataBg}`}>
                    <td className="py-2 px-2 font-medium text-slate-700">{row.dealer}</td>
                    <td className="py-2 px-2 text-center"><TierBadge tier={row.tier} /></td>
                    <td className="py-2 px-2 text-right font-mono text-slate-700">{row.tahmin}</td>
                    <td className="py-2 px-2 text-right font-mono text-slate-700">{row.gercek}</td>
                    <td className={`py-2 px-2 text-right font-mono font-semibold ${hataRenk}`}>
                      {row.hata_pct != null ? `${row.hata_pct > 0 ? '+' : ''}${row.hata_pct.toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2 px-3"><ModelChips mix={row.model_mix} /></td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-50">
                <td className="py-2 px-2 font-bold text-slate-800">TOPLAM</td>
                <td />
                <td className="py-2 px-2 text-right font-bold font-mono text-blue-700">
                  {sortedBayiler.reduce((s, r) => s + r.tahmin, 0)}
                </td>
                <td className="py-2 px-2 text-right font-bold font-mono text-slate-800">
                  {sortedBayiler.reduce((s, r) => s + r.gercek, 0)}
                </td>
                <td className="py-2 px-2 text-right font-semibold text-slate-500">—</td>
                <td className="py-2 px-3 text-xs text-slate-400">son 12 ay mix</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Renk: yeşil &lt;10% · sarı 10–20% · kırmızı &gt;20% mutlak hata
        </p>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sekme 2: 2026 Yıllık Plan — İki Senaryo
// ---------------------------------------------------------------------------

function SenaryoView({ senaryo, metodoloji }: { senaryo: Senaryo; metodoloji: Metodoloji[] }) {
  const { ozet, aylik, ocak_bayi_dagilim } = senaryo
  const LANSMAN_AY = ozet.lansman_ay
  const barRenk = (ay: number) =>
    ay === LANSMAN_AY ? '#22c55e' : ay >= LANSMAN_AY ? '#3b82f6' : '#94a3b8'
  const ocakToplam = ocak_bayi_dagilim.reduce((s, r) => s + r.adet, 0)

  return (
    <div className="space-y-6">
      {/* Özet kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Yıllık Hedef" value={ozet.yillik_hedef.toLocaleString('tr')} sub="araç (2026)"
          colorClass="bg-blue-50 border-blue-200" />
        <MetricCard label="Ocak 2026" value={ozet.ocak_hedef.toLocaleString('tr')} sub="araç (SI bazlı)"
          colorClass="bg-slate-50 border-slate-200" />
        <MetricCard label="Lansman Ayı" value="Mart 2026" sub={`×${ozet.lansman_boost} boost`}
          colorClass="bg-green-50 border-green-200" />
        <MetricCard label="Doğrulama" value={ozet.toplam_kontrol.toLocaleString('tr')}
          sub={ozet.toplam_kontrol === ozet.yillik_hedef ? '= hedef ✓' : '≠ hedef!'}
          colorClass={ozet.toplam_kontrol === ozet.yillik_hedef ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} />
      </div>

      {/* Aylık bar chart */}
      <Card title={`${ozet.yillik_hedef.toLocaleString('tr')} Araç — Aylık Dağıtım Hedefi`}>
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
              {aylik.map(row => <Cell key={row.ay} fill={barRenk(row.ay)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 justify-center text-xs text-slate-500">
          <span><span className="inline-block w-3 h-3 rounded bg-slate-300 mr-1" />Ocak–Şubat</span>
          <span><span className="inline-block w-3 h-3 rounded bg-green-500 mr-1" />Mart (lansman ×{ozet.lansman_boost})</span>
          <span><span className="inline-block w-3 h-3 rounded bg-blue-500 mr-1" />Nisan–Aralık</span>
        </div>
      </Card>

      {/* Metodoloji */}
      <div className="bg-green-50 rounded-xl border border-green-200 p-4">
        <p className="text-sm font-semibold text-green-800 mb-2">Metodoloji</p>
        <ul className="space-y-1">
          {metodoloji.map(m => (
            <li key={m.baslik} className="text-xs text-green-700">
              <span className="font-medium">{m.baslik}:</span> {m.aciklama}
            </li>
          ))}
        </ul>
      </div>

      {/* Ocak 2026 Bayi Dağılımı */}
      <Card title={`Ocak 2026 Bayi Dağılımı (Toplam: ${ocakToplam} araç)`}>
        <div className="flex gap-4 mb-3 text-xs text-slate-500 flex-wrap">
          <span>Ağırlık: <strong>50%</strong> son 12 ay satış payı</span>
          <span>+ <strong>30%</strong> Ocak 2026 hedef payı</span>
          <span>+ <strong>20%</strong> performans skoru</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-2 font-medium text-slate-500">Bayi</th>
                <th className="text-center py-2 px-2 font-medium text-slate-500">Tier</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Adet</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Pay%</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Jan26 Hedef</th>
                <th className="text-right py-2 px-2 font-medium text-slate-500">Perf.</th>
                <th className="text-center py-2 px-2 font-medium text-slate-500">Güven</th>
                <th className="text-left py-2 px-3 font-medium text-slate-500">Model Mix</th>
              </tr>
            </thead>
            <tbody>
              {ocak_bayi_dagilim.map(row => (
                <tr key={row.dealer} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 px-2 font-medium text-slate-700">{row.dealer}</td>
                  <td className="py-2 px-2 text-center"><TierBadge tier={row.tier} /></td>
                  <td className="py-2 px-2 text-right font-mono font-semibold text-blue-700">{row.adet}</td>
                  <td className="py-2 px-2 text-right font-mono text-slate-600">
                    {row.pay_pct.toFixed(1)}%
                    <div className="w-full bg-slate-100 rounded-full h-1 mt-0.5">
                      <div className="h-1 rounded-full bg-blue-400" style={{ width: `${Math.min(100, row.pay_pct * 4)}%` }} />
                    </div>
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-slate-500">{row.jan26_hedef}</td>
                  <td className="py-2 px-2 text-right font-mono text-slate-500">{(row.perf_skoru * 100).toFixed(0)}%</td>
                  <td className="py-2 px-2 text-center"><GercekcilikBadge seviye={row.gercekci_mi} /></td>
                  <td className="py-2 px-3"><ModelChips mix={row.model_mix} /></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-50">
                <td className="py-2 px-2 font-bold text-slate-800">TOPLAM</td>
                <td />
                <td className="py-2 px-2 text-right font-bold font-mono text-blue-700">{ocakToplam}</td>
                <td className="py-2 px-2 text-right font-mono font-bold text-slate-600">100%</td>
                <td className="py-2 px-2 text-right font-mono text-slate-500">
                  {ocak_bayi_dagilim.reduce((s, r) => s + r.jan26_hedef, 0)}
                </td>
                <td colSpan={3} className="py-2 px-2 text-xs text-slate-400 text-center">
                  {ocakToplam === ozet.ocak_hedef ? `✓ ${ozet.ocak_hedef} araç` : `${ocakToplam} ≠ ${ozet.ocak_hedef}!`}
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

function Plan2026Tab({ data }: { data: Plan2026 }) {
  const [aktifSenaryo, setAktifSenaryo] = useState<8500 | 10000>(8500)
  const senaryo = aktifSenaryo === 8500 ? data.senaryo_8500 : data.senaryo_10000

  const s8 = data.senaryo_8500.ozet
  const s10 = data.senaryo_10000.ozet

  return (
    <div className="space-y-6">
      {/* Senaryo seçici */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">2026 Hedef Senaryosu</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {([8500, 10000] as const).map(h => (
            <button key={h} onClick={() => setAktifSenaryo(h)}
              className={`p-4 rounded-xl border-2 text-left transition-all ${
                aktifSenaryo === h
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-lg font-bold ${aktifSenaryo === h ? 'text-blue-700' : 'text-slate-700'}`}>
                  {h.toLocaleString('tr')} Araç
                </span>
                {aktifSenaryo === h && (
                  <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full font-medium">Aktif</span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                {h === 8500
                  ? `Mevcut büyüme trendi · Ocak: ${s8.ocak_hedef} araç (SI bazlı)`
                  : `Agresif büyüme (~+%${Math.round((10000 / 8500 - 1) * 100)}) · Ocak: ${s10.ocak_hedef} araç (SI bazlı)`}
              </p>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                {(h === 8500 ? data.senaryo_8500 : data.senaryo_10000).aylik
                  .filter(r => [1, 3, 12].includes(r.ay))
                  .map(r => (
                    <div key={r.ay}>
                      <p className="text-xs text-slate-400">{r.ay_adi}</p>
                      <p className="text-sm font-semibold text-slate-700">{r.hedef}</p>
                    </div>
                  ))}
              </div>
            </button>
          ))}
        </div>
      </div>

      <SenaryoView senaryo={senaryo} metodoloji={data.metodoloji} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ana bileşen
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
      <div className="flex items-center justify-center h-64 text-slate-400">Yükleniyor…</div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Tahmin & Plan</h1>
        <p className="text-slate-500 text-sm mt-1">
          Aralık 2025 geriye dönük tahmin doğrulaması (A/B/C tier bazlı) · 2026 yıllık iki senaryo
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
