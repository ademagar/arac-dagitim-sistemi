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

interface VeriKaynagi {
  dosya: string
  icerik: string
  kullanim: string | string[]
  not?: string
}

interface ModelAralikAnalizSatir {
  model: string
  aciklama: string
  gercek_adet: number
  gercek_pay: number
  son6_pay: number
  lansman_model: boolean
}

interface AralikTahmin {
  ozet: AralikOzet
  tier_ozet: TierOzet[]
  bayi_tahmin: BayiTahmin[]
  aylik_trend: AylikTrend[]
  metodoloji: Metodoloji[]
  model_aralik_analiz: ModelAralikAnalizSatir[]
  veri_kaynaklari: VeriKaynagi[]
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

interface ModelDagilim {
  model: string
  aciklama: string
  pay_pct: number
  adet: number
  lansman_model: boolean
}

interface ModelAylikSatir {
  ay: number
  ay_adi: string
  toplam_hedef: number
  lansman: boolean
  model_dagilim: ModelDagilim[]
}

interface Senaryo {
  ozet: Plan2026Ozet
  aylik: AylikPlan[]
  ocak_bayi_dagilim: OcakBayiDagilim[]
  model_aylik: ModelAylikSatir[]
}

interface StratejikNeden {
  baslik: string
  aciklama: string
}

interface StratejikBaglamOcakSubat {
  baslik: string
  durum: string
  nedenler: StratejikNeden[]
  yorum: string
}

interface StratejikBaglamMart {
  baslik: string
  aciklama: string
  etkiler: string[]
}

interface StratejikBaglamModel {
  baslik: string
  mevcut_durum: string
  '2026_beklenti': string
}

interface BoostJustifikasyon {
  b1_2024_mart_satis: number
  b1_2024_aylik_ort: number
  b1_mart_si_2024: number
  b1_2025_mart_satis: number
  b1_2025_aylik_ort: number
  b1_mart_si_2025: number
  b1_lansman_etkisi: number
  b1_market_payi: number
  hesaplanan_boost: number
  uygulanan_boost: number
  muhafazakarlik: string
}

interface StratejikBaglamlar {
  ocak_subat_analizi: StratejikBaglamOcakSubat
  mart_lansman_stratejisi: StratejikBaglamMart
  model_yorumu: StratejikBaglamModel
  boost_justifikasyon?: BoostJustifikasyon
}

interface Plan2026 {
  senaryo_8500: Senaryo
  senaryo_10000: Senaryo
  metodoloji: Metodoloji[]
  stratejik_baglamlar: StratejikBaglamlar
}

interface BayiAylikModelHedef {
  ay: number
  ay_adi: string
  toplam: number
  modeller: Record<string, number>
}

interface BayiHedef {
  tier: 'A' | 'B' | 'C'
  aylik: BayiAylikModelHedef[]
  yillik_toplam: number
  yillik_modeller: Record<string, number>
  yillik_segmentler: Record<string, number>
}

interface BayiAylikHedefler {
  [dealer: string]: BayiHedef
}

interface TahminData {
  aralik_tahmin: AralikTahmin
  plan_2026: Plan2026
  bayi_aylik_hedefler: {
    senaryo_8500: BayiAylikHedefler
    senaryo_10000: BayiAylikHedefler
  }
}

// ---------------------------------------------------------------------------
// Ortak yardımcı bileşenler
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

function Card({ title, children, className }: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-slate-200 p-5 ${className ?? ''}`}>
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

const MODEL_COLORS: Record<string, string> = {
  // A Segmenti versiyonları - mavi tonlar
  A1: 'bg-blue-50 text-blue-700 border border-blue-200',
  A2: 'bg-blue-200 text-blue-900 border border-blue-300',
  A3: 'bg-blue-100 text-blue-800 border border-blue-300',
  // B Segmenti versiyonları - amber/turuncu tonlar
  B1: 'bg-amber-100 text-amber-900 border border-amber-300',
  B2: 'bg-amber-50 text-amber-700 border border-amber-200',
  // C Segmenti - rose/kırmızı
  C1: 'bg-rose-100 text-rose-800 border border-rose-200',
  // D Segmenti - slate
  D1: 'bg-slate-100 text-slate-600 border border-slate-200',
}

function ModelChips({ mix }: { mix: Record<string, number> }) {
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
// Açıklama ve veri kaynağı bileşenleri
// ---------------------------------------------------------------------------

function BilgiKutusu({
  baslik, renk = 'blue', children,
}: {
  baslik: string
  renk?: 'blue' | 'amber' | 'green' | 'slate'
  children: React.ReactNode
}) {
  const renkler = {
    blue:  { bg: 'bg-blue-50',  border: 'border-blue-200',  title: 'text-blue-800',  body: 'text-blue-700' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', title: 'text-amber-800', body: 'text-amber-700' },
    green: { bg: 'bg-green-50', border: 'border-green-200', title: 'text-green-800', body: 'text-green-700' },
    slate: { bg: 'bg-slate-800', border: 'border-slate-700', title: 'text-white',    body: 'text-slate-300' },
  }
  const r = renkler[renk]
  return (
    <div className={`rounded-xl border ${r.bg} ${r.border} p-5`}>
      <p className={`text-sm font-semibold ${r.title} mb-3`}>{baslik}</p>
      <div className={`text-xs space-y-2 ${r.body}`}>{children}</div>
    </div>
  )
}

function VeriKaynaklariPanel({ kaynaklar }: { kaynaklar: VeriKaynagi[] }) {
  const [acik, setAcik] = useState(false)
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <button
        onClick={() => setAcik(a => !a)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors"
      >
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Veri Kaynakları ({kaynaklar.length} dosya)
        </span>
        <span className="text-slate-400 text-sm">{acik ? '↑' : '↓'}</span>
      </button>
      {acik && (
        <div className="px-5 pb-5 space-y-3 border-t border-slate-100 pt-4">
          {kaynaklar.map(k => (
            <div key={k.dosya} className="border border-slate-200 rounded-lg p-3">
              <p className="text-xs font-mono font-semibold text-blue-700 mb-1">📄 {k.dosya}</p>
              <p className="text-xs text-slate-600 mb-2">{k.icerik}</p>
              {Array.isArray(k.kullanim) ? (
                <ul className="space-y-0.5">
                  {k.kullanim.map((u, i) => (
                    <li key={i} className="text-xs text-slate-500">→ {u}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">→ {k.kullanim}</p>
              )}
              {k.not && (
                <p className="text-xs text-slate-400 italic mt-1 border-t border-slate-100 pt-1">
                  Not: {k.not}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function MetodolojiBlogu({ maddeler }: { maddeler: Metodoloji[] }) {
  return (
    <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
      <p className="text-sm font-semibold text-blue-800 mb-3">Metodoloji Adımları</p>
      <ol className="space-y-2">
        {maddeler.map((m, i) => (
          <li key={m.baslik} className="flex gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold mt-0.5">
              {i + 1}
            </span>
            <div>
              <p className="text-xs font-semibold text-blue-800">{m.baslik}</p>
              <p className="text-xs text-blue-700 mt-0.5">{m.aciklama}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
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

function ModelAralikAnaliz({ satirlar }: { satirlar: ModelAralikAnalizSatir[] }) {
  const MODEL_COLORS: Record<string, string> = {
    A1: 'bg-violet-600', A2: 'bg-blue-500', A3: 'bg-sky-400',
    B1: 'bg-amber-500', B2: 'bg-orange-400', C1: 'bg-rose-400', D1: 'bg-slate-400',
  }
  return (
    <Card title="Aralık 2025 Model Bazlı Gerçekleşme">
      <p className="text-xs text-slate-500 mb-3">
        Aşağıdaki tablo, Aralık 2025'te fiilen satılan araçların model dağılımını gösterir.
        Son 6 ay payı ile karşılaştırarak hangi modelin akselerasyona girdiğini (A1) ve hangisinin
        gerilediğini (C1) görebilirsiniz.
      </p>
      <div className="space-y-2">
        {satirlar.map(row => (
          <div key={row.model} className={`flex items-center gap-3 p-2 rounded-lg border ${
            row.lansman_model ? 'bg-violet-50 border-violet-200' : 'bg-white border-slate-100'
          }`}>
            <div className="flex items-center gap-2 w-32 flex-shrink-0">
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${MODEL_COLORS[row.model] ?? 'bg-slate-400'}`} />
              <span className="text-xs font-bold text-slate-700">{row.model}</span>
              {row.lansman_model && (
                <span className="text-xs bg-violet-600 text-white px-1 py-0.5 rounded font-medium">YENİ</span>
              )}
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-500">{row.aciklama}</p>
            </div>
            <div className="text-right w-20 flex-shrink-0">
              <p className="text-xs font-bold text-slate-800">{row.gercek_adet} araç</p>
              <p className="text-xs text-slate-500">Ara'25: {row.gercek_pay}%</p>
            </div>
            <div className="text-right w-20 flex-shrink-0">
              <p className="text-xs text-slate-500">Son 6 ay: {row.son6_pay}%</p>
              <div className="w-full bg-slate-100 rounded-full h-1 mt-0.5">
                <div
                  className={`h-1 rounded-full ${MODEL_COLORS[row.model] ?? 'bg-slate-400'}`}
                  style={{ width: `${Math.min(100, row.son6_pay * 1.5)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-3">
        <span className="text-violet-600 font-medium">YENİ</span> = A1 modeli Eylül 2025'ten itibaren piyasada.
        <span className="text-amber-600 font-medium ml-2">LANSMAN</span> = B1 (Premium SUV) yeni versiyon
        Mart 2026'da çıkıyor — Aralık'ta B1 payı (%11) düşmüş görünse de lansman öncesi stok yönetimi etkisi.
        C1 modelinin Aralık payı (%3) Ocak payına (%42) göre dramatik düşüş gösterdi.
      </p>
    </Card>
  )
}

function AralikTab({ data }: { data: AralikTahmin }) {
  const [sortField, setSortField] = useState<'hata_pct' | 'gercek' | 'tahmin'>('hata_pct')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [filterTier, setFilterTier] = useState<'Tümü' | 'A' | 'B' | 'C'>('Tümü')

  const { ozet, tier_ozet, bayi_tahmin, aylik_trend, metodoloji,
          model_aralik_analiz, veri_kaynaklari } = data

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

      {/* Bağlam açıklaması */}
      <BilgiKutusu baslik="Bu Sekme: Aralık 2025 Geriye Dönük Tahmin Doğrulaması" renk="slate">
        <p>
          <strong className="text-white">Amaç:</strong>{' '}
          Modelimizin ne kadar doğru tahmin ürettiğini ölçmek için Aralık 2025 verisini
          kullandık. Modeli Kasım 2025 verisine kadar eğittik, Aralık tahminini ürettik,
          sonra gerçek Aralık satışlarıyla kıyasladık.
        </p>
        <p>
          <strong className="text-white">Yaklaşım — A/B/C Tier Gruplandırması:</strong>{' '}
          28 bayi, bölgesel satış potansiyeline göre 3 gruba ayrıldı.
          Tier A (Marmara, Ege, İç Anadolu) yüksek hacimli 21 bayi,
          Tier B (Akdeniz) 4 bayi,
          Tier C (Güneydoğu, Karadeniz) 3 bayi.
          Her tier için ayrı Seasonal Index ve ayrı trend düzeltmesi hesaplandı.
          Tekli model MAPE'si %12.02'den tier bazlı modelde <strong className="text-green-400">%7.82</strong>'ye düştü.
        </p>
        <p>
          <strong className="text-white">Seasonal Index (SI) Nedir?</strong>{' '}
          SI, ilgili ayın yıl boyunca diğer aylara kıyasla ne kadar satış aldığını gösteren orandır.
          SI=1.32 (Aralık) → o ay yıllık ortalamanın %32 üzerinde satış yapıldığı anlamına gelir.
          Tier bazlı SI, her grup için 2024-2025 verisiyle hesaplandı ve global SI ile harmanlandı.
        </p>
        <p>
          <strong className="text-white">Trend Düzeltmesi:</strong>{' '}
          Son 6 ay ortalaması / önceki 6 ay ortalaması oranı, [0.80, 1.35] aralığında sınırlandırıldı.
          2025'te gerçek büyüme oranı 1.247 olduğundan üst sınır 1.20'den 1.35'e yükseltildi.
        </p>
        <p>
          <strong className="text-white">Önemli Sınır:</strong>{' '}
          Model istatistiksel bir araçtır. Stok kısıtı, lansman stratejisi ve bayi davranışı
          gibi operasyonel faktörleri tam olarak yansıtamaz.
        </p>
      </BilgiKutusu>

      {/* Özet metrik kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Tahmin" value={ozet.toplam_tahmin.toLocaleString('tr')} sub="araç"
          colorClass="bg-blue-50 border-blue-200" />
        <MetricCard label="Gerçek" value={ozet.toplam_gercek.toLocaleString('tr')} sub="araç (Ara 2025)"
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
        <p className="text-xs text-slate-400 mb-3">
          Her tier için bağımsız SI ve trend hesaplandı. Tier içindeki toplam araç sayısı tahmin edildi;
          ardından o tierin bayileri arasında son 12 aylık satış payına göre dağıtıldı.
        </p>
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
                  <p className="text-xs text-slate-400">SI (Aralık)</p>
                  <p className="text-xs font-mono font-semibold text-slate-700">{t.si.toFixed(3)}</p>
                  <p className="text-xs text-slate-400">mevsimsel idx</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Trend</p>
                  <p className="text-xs font-mono font-semibold text-slate-700">{t.trend.toFixed(3)}</p>
                  <p className="text-xs text-slate-400">son6/önceki6</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Son 12 ay ort.</p>
                  <p className="text-xs font-mono font-semibold text-slate-700">{t.son12_ort.toFixed(0)}</p>
                  <p className="text-xs text-slate-400">araç/ay</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metodoloji */}
      <MetodolojiBlogu maddeler={metodoloji} />

      {/* Aylık trend grafiği */}
      <Card title="Aylık Satış Trendi (Ocak 2024 – Aralık 2025)">
        <p className="text-xs text-slate-500 mb-3">
          Mavi çizgi: 2024-2025 boyunca gerçekleşen aylık araç satışları.
          Kırmızı nokta: Modelimizin Aralık 2025 için ürettiği tahmin (460 araç).
          Gerçek: 499 araç — MAPE %7.82.
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ left: 0, right: 20, top: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="ym" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(2)} interval={1} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v: number, name: string) => [
                v?.toLocaleString('tr'),
                name === 'gercek' ? 'Gerçek Satış' : 'Tahmin (Ara 2025)',
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
      </Card>

      {/* Model bazlı Aralık analizi */}
      {model_aralik_analiz && model_aralik_analiz.length > 0 && (
        <ModelAralikAnaliz satirlar={model_aralik_analiz} />
      )}

      {/* Bayi tahmin tablosu */}
      <Card title="Bayi Bazında Tahmin vs Gerçek">
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <p className="text-xs text-slate-500">
            Her bayinin tahmini = tier tahmini × bayinin tier içindeki son 12 ay satış payı.
            Sütun başlıklarına tıklayarak sıralayabilirsiniz.
          </p>
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
                <th className="text-left py-2 px-3 font-medium text-slate-500">Son 12 Ay Model Mix</th>
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

      {/* Veri kaynakları */}
      <VeriKaynaklariPanel kaynaklar={veri_kaynaklari} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Aylık Model Hedefleri Tablosu
// ---------------------------------------------------------------------------

const MODEL_BG: Record<string, string> = {
  A1: 'bg-violet-100 text-violet-800',
  A2: 'bg-blue-100 text-blue-800',
  A3: 'bg-sky-100 text-sky-800',
  B1: 'bg-amber-100 text-amber-800',
  B2: 'bg-orange-100 text-orange-800',
  C1: 'bg-rose-100 text-rose-800',
  D1: 'bg-slate-100 text-slate-600',
  'Diğer': 'bg-slate-100 text-slate-500',
}

function AylikModelTablosu({
  modelAylik, yillikHedef, lansman_ay,
}: {
  modelAylik: ModelAylikSatir[]
  yillikHedef: number
  lansman_ay: number
}) {
  const allModels = [...new Set(
    modelAylik.flatMap(ay => ay.model_dagilim.map(m => m.model))
  )]
  const modelTotals: Record<string, number> = {}
  for (const ay of modelAylik) {
    for (const m of ay.model_dagilim) {
      modelTotals[m.model] = (modelTotals[m.model] || 0) + m.adet
    }
  }
  const sortedModels = allModels
    .filter(m => m !== 'Diğer')
    .sort((a, b) => (modelTotals[b] || 0) - (modelTotals[a] || 0))
  if (allModels.includes('Diğer')) sortedModels.push('Diğer')

  const getAdet = (ay: ModelAylikSatir, model: string): number =>
    ay.model_dagilim.find(m => m.model === model)?.adet || 0

  const getLansmanModel = (ay: ModelAylikSatir): string | null => {
    const lm = ay.model_dagilim.find(m => m.lansman_model)
    return lm ? lm.model : null
  }

  return (
    <div>
      <div className="mb-4">
        <BilgiKutusu baslik="Aylık Model Bazlı Hedef Tablosu — Nasıl Okunur?" renk="blue">
          <p>
            <strong>Yöntem:</strong> Her ayın toplam araç hedefi, o ayın tarihsel model karışımına
            (model mix) göre modellere dağıtıldı.
            Son 6 ay verisi %60, önceki 18 ay %40 ağırlıkla harmanlandı.
            Bu, A1 gibi yeni giren modellere daha fazla ağırlık verir.
          </p>
          <p>
            <strong>Lansman Etkisi:</strong> Mart ve sonrası için B1 (yeni versiyon)
            payı +%30 artırıldı ve toplam normalize edildi.
            Bu, B1 yeni versiyonunun Mart 2026 lansmanındaki talep artışını yansıtır.
          </p>
          <p>
            <strong>Dikkat — C1 Trendi:</strong> Ocak 2026 için C1 payı historik Ocak verisine
            göre yüksek görünüyor. Gerçekte C1, 2025 sonunda ciddi geriledi
            (Ocak %42 → Aralık %3). Bu tabloyu kullanırken C1 hedeflerini
            aşağı revize etmenizi öneririz.
          </p>
        </BilgiKutusu>
      </div>

      {/* Model göstergesi */}
      <div className="flex flex-wrap gap-2 mb-4">
        {sortedModels.map(m => {
          const info = modelAylik[0]?.model_dagilim.find(md => md.model === m)
          return (
            <div key={m} className={`px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 ${MODEL_BG[m] ?? 'bg-slate-100 text-slate-600'}`}>
              {m === 'B1' && <span className="text-xs">🚀</span>}
              <span className="font-bold">{m}</span>
              {info?.aciklama && <span className="opacity-70">{info.aciklama}</span>}
              <span className="font-bold">— {(modelTotals[m] || 0).toLocaleString('tr')} araç/yıl</span>
            </div>
          )
        })}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-800 text-white">
              <th className="text-left py-3 px-3 font-semibold sticky left-0 bg-slate-800 z-10 min-w-[90px]">
                Ay
              </th>
              <th className="text-right py-3 px-3 font-semibold min-w-[70px] border-r border-slate-600">
                Toplam
              </th>
              {sortedModels.map(m => (
                <th key={m} className={`text-right py-3 px-3 font-semibold min-w-[75px] ${
                  m === 'B1' ? 'bg-amber-900' : ''
                }`}>
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {modelAylik.map((ay, idx) => {
              const isLansman = ay.ay === lansman_ay
              const lansmanModel = getLansmanModel(ay)
              return (
                <tr key={ay.ay}
                  className={`border-b border-slate-100 ${
                    isLansman ? 'bg-green-50 font-semibold' :
                    idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'
                  }`}
                >
                  <td className={`py-2.5 px-3 sticky left-0 z-10 font-semibold ${
                    isLansman ? 'bg-green-50 text-green-800' : 'bg-inherit text-slate-700'
                  }`}>
                    <div className="flex items-center gap-1">
                      {ay.ay_adi}
                      {isLansman && (
                        <span className="text-xs bg-green-600 text-white px-1 rounded font-medium">LANSMAN</span>
                      )}
                      {!isLansman && ay.lansman && lansmanModel && (
                        <span className="text-xs text-green-600">+A1</span>
                      )}
                    </div>
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold border-r border-slate-200 ${
                    isLansman ? 'text-green-800' : 'text-slate-800'
                  }`}>
                    {ay.toplam_hedef.toLocaleString('tr')}
                  </td>
                  {sortedModels.map(m => {
                    const adet = getAdet(ay, m)
                    const isLansmanModelCol = m === 'B1'
                    return (
                      <td key={m} className={`py-2.5 px-3 text-right font-mono ${
                        isLansmanModelCol && adet > 0 ? 'text-violet-700 font-semibold' :
                        adet === 0 ? 'text-slate-300' : 'text-slate-600'
                      }`}>
                        {adet > 0 ? adet.toLocaleString('tr') : '—'}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="bg-slate-100 font-bold border-t-2 border-slate-300">
              <td className="py-3 px-3 text-slate-800 sticky left-0 bg-slate-100">YIL TOPLAMI</td>
              <td className="py-3 px-3 text-right text-blue-700 border-r border-slate-300">
                {yillikHedef.toLocaleString('tr')}
              </td>
              {sortedModels.map(m => (
                <td key={m} className={`py-3 px-3 text-right font-mono ${
                  m === 'B1' ? 'text-amber-700' : 'text-slate-700'
                }`}>
                  {(modelTotals[m] || 0).toLocaleString('tr')}
                  <span className="block text-xs font-normal text-slate-400">
                    {yillikHedef > 0 ? `${((modelTotals[m] || 0) / yillikHedef * 100).toFixed(1)}%` : ''}
                  </span>
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-2">
        🚀 B1 = Lansman modeli (yeni versiyon Mart 2026) · LANSMAN satırı = Mart 2026 (×1.15 boost aylık toplama uygulandı)
        · A1 = Eylül 2025'ten itibaren organik büyüyen yeni model
        · Sütun altları: model bazında yıllık pay
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stratejik Bağlam Paneli
// ---------------------------------------------------------------------------

function BoostJustifikasyonPanel({ bj }: { bj: BoostJustifikasyon }) {
  return (
    <div className="bg-indigo-50 rounded-lg border border-indigo-200 p-4 mt-3">
      <p className="text-xs font-semibold text-indigo-800 mb-2 uppercase tracking-wide">
        1.15 Boost — İstatistiksel Gerekçe
      </p>
      <ul className="space-y-1.5 text-xs text-indigo-700">
        <li>
          <span className="font-semibold">B1 Mart SI (2024 — lansman yılı):</span>{' '}
          {bj.b1_mart_si_2024.toFixed(3)}{' '}
          <span className="text-indigo-500">
            ({bj.b1_2024_mart_satis} araç / aylık ort. {bj.b1_2024_aylik_ort} araç)
          </span>
        </li>
        <li>
          <span className="font-semibold">B1 Mart SI (2025 — normal yıl):</span>{' '}
          {bj.b1_mart_si_2025.toFixed(3)}{' '}
          <span className="text-indigo-500">
            ({bj.b1_2025_mart_satis} araç / aylık ort. {bj.b1_2025_aylik_ort} araç)
          </span>
        </li>
        <li>
          <span className="font-semibold">Yeni versiyon lansmanının B1 üzerindeki etki:</span>{' '}
          {bj.b1_mart_si_2024.toFixed(3)} / {bj.b1_mart_si_2025.toFixed(3)}{' '}
          = <strong className="text-indigo-900">{bj.b1_lansman_etkisi.toFixed(3)}</strong>{' '}
          <span className="text-indigo-500">(+%{((bj.b1_lansman_etkisi - 1) * 100).toFixed(0)})</span>
        </li>
        <li>
          <span className="font-semibold">B1 market payı (2024–2025 toplam satışlar):</span>{' '}
          %{(bj.b1_market_payi * 100).toFixed(1)}
        </li>
        <li>
          <span className="font-semibold">Aggregate hesaplama:</span>{' '}
          1 + ({bj.b1_market_payi.toFixed(3)} × {(bj.b1_lansman_etkisi - 1).toFixed(3)}){' '}
          = <strong className="text-indigo-900">{bj.hesaplanan_boost.toFixed(3)}</strong>
        </li>
        <li className="bg-indigo-100 rounded px-2 py-1">
          <span className="font-semibold">Muhafazakârlık:</span>{' '}
          {bj.muhafazakarlik}
        </li>
      </ul>
    </div>
  )
}

function StratejikBaglamPanel({ baglam }: { baglam: StratejikBaglamlar }) {
  const [expanded, setExpanded] = useState(false)
  const { ocak_subat_analizi: osa, mart_lansman_stratejisi: mls, model_yorumu: my } = baglam

  return (
    <div className="bg-amber-50 rounded-xl border border-amber-200 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-sm font-semibold text-amber-800 mb-1">
            ⚠️ Stratejik Bağlam — Neden Ocak-Şubat Düşük?
          </p>
          <p className="text-xs text-amber-700">{osa.durum}</p>
        </div>
        <button onClick={() => setExpanded(e => !e)}
          className="text-xs text-amber-600 hover:text-amber-800 flex-shrink-0 font-semibold border border-amber-300 px-3 py-1 rounded-lg"
        >
          {expanded ? 'Kapat ↑' : 'Detay ↓'}
        </button>
      </div>

      {expanded && (
        <div className="mt-5 space-y-4">
          <div>
            <p className="text-xs font-semibold text-amber-800 mb-2 uppercase tracking-wide">
              {osa.baslik}
            </p>
            <div className="space-y-2">
              {osa.nedenler.map(n => (
                <div key={n.baslik} className="bg-white rounded-lg border border-amber-200 p-3">
                  <p className="text-xs font-semibold text-amber-800 mb-1">{n.baslik}</p>
                  <p className="text-xs text-amber-700">{n.aciklama}</p>
                </div>
              ))}
            </div>
            <div className="bg-amber-100 rounded-lg p-3 mt-2">
              <p className="text-xs font-semibold text-amber-800 mb-1">Sonuç / Yorum</p>
              <p className="text-xs text-amber-700">{osa.yorum}</p>
            </div>
          </div>

          <div className="bg-green-50 rounded-lg border border-green-200 p-4">
            <p className="text-xs font-semibold text-green-800 mb-1">{mls.baslik}</p>
            <p className="text-xs text-green-700 mb-2">{mls.aciklama}</p>
            <ul className="space-y-1">
              {mls.etkiler.map((e, i) => (
                <li key={i} className="text-xs text-green-600 flex gap-1">
                  <span className="text-green-400">•</span> {e}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-violet-50 rounded-lg border border-violet-200 p-4">
            <p className="text-xs font-semibold text-violet-800 mb-1">{my.baslik}</p>
            <p className="text-xs text-violet-700 mb-1">
              <strong>Mevcut Durum (2025 sonu):</strong> {my.mevcut_durum}
            </p>
            <p className="text-xs text-violet-700">
              <strong>2026 Beklentisi:</strong> {my['2026_beklenti']}
            </p>
          </div>

          {baglam.boost_justifikasyon && (
            <BoostJustifikasyonPanel bj={baglam.boost_justifikasyon} />
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sekme 2: 2026 Yıllık Plan — İki Senaryo
// ---------------------------------------------------------------------------

function SenaryoView({
  senaryo, metodoloji, stratejikBaglam,
}: {
  senaryo: Senaryo
  metodoloji: Metodoloji[]
  stratejikBaglam: StratejikBaglamlar
}) {
  const [subTab, setSubTab] = useState(0)
  const { ozet, aylik, ocak_bayi_dagilim, model_aylik } = senaryo
  const LANSMAN_AY = ozet.lansman_ay
  const barRenk = (ay: number) =>
    ay === LANSMAN_AY ? '#22c55e' : ay >= LANSMAN_AY ? '#3b82f6' : '#94a3b8'
  const ocakToplam = ocak_bayi_dagilim.reduce((s, r) => s + r.adet, 0)

  return (
    <div className="space-y-5">
      {/* Özet kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Yıllık Hedef" value={ozet.yillik_hedef.toLocaleString('tr')} sub="araç (2026)"
          colorClass="bg-blue-50 border-blue-200" />
        <MetricCard label="Ocak 2026" value={ozet.ocak_hedef.toLocaleString('tr')} sub="araç (SI bazlı)"
          colorClass="bg-slate-50 border-slate-200" />
        <MetricCard label="Lansman Ayı" value="Mart 2026" sub={`×${ozet.lansman_boost} SI boost`}
          colorClass="bg-green-50 border-green-200" />
        <MetricCard label="Doğrulama" value={ozet.toplam_kontrol.toLocaleString('tr')}
          sub={ozet.toplam_kontrol === ozet.yillik_hedef ? '= hedef ✓' : '≠ hedef!'}
          colorClass={ozet.toplam_kontrol === ozet.yillik_hedef ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} />
      </div>

      {/* Stratejik bağlam */}
      <StratejikBaglamPanel baglam={stratejikBaglam} />

      {/* Sub-tab: Aylık Plan vs Model Hedefleri */}
      <TabBar
        tabs={['Aylık Plan', 'Model Hedefleri (Oca–Ara)']}
        active={subTab}
        onChange={setSubTab}
      />

      {subTab === 0 && (
        <div className="space-y-5">
          {/* Aylık bar chart */}
          <Card title={`${ozet.yillik_hedef.toLocaleString('tr')} Araç — Aylık Dağıtım Hedefi`}>
            <p className="text-xs text-slate-500 mb-3">
              Her ayın hedefi = Yıllık hedef × (o ayın SI payı). Mart+ için SI ×{ozet.lansman_boost} boost uygulandı.
              Ocak SI ≈ 0.66 → yılın en düşük hedefi. Aralık SI ≈ 1.62 → yılın en yüksek hedefi.
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={aylik} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="ay_adi" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  formatter={(v: number, _: string, props: { payload?: { si?: number; lansman_boost?: number } }) => [
                    `${v.toLocaleString('tr')} araç`,
                    `Hedef (SI=${props.payload?.si?.toFixed(3) ?? ''}${props.payload?.lansman_boost && props.payload.lansman_boost > 1 ? ' ×' + props.payload.lansman_boost : ''})`,
                  ]}
                  labelFormatter={label => `${label} 2026`}
                />
                <ReferenceLine y={ozet.yillik_hedef / 12} stroke="#94a3b8" strokeDasharray="4 4"
                  label={{ value: 'Aylık ort.', fontSize: 9, fill: '#94a3b8' }} />
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

          {/* Aylık detay tablosu */}
          <Card title="Aylık Hedef Detayı">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 font-medium text-slate-500">Ay</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Hedef</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Pay%</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">SI</th>
                    <th className="text-left py-2 px-2 font-medium text-slate-500">SI Bar</th>
                  </tr>
                </thead>
                <tbody>
                  {aylik.map(row => (
                    <tr key={row.ay} className={`border-b border-slate-100 ${
                      row.ay === LANSMAN_AY ? 'bg-green-50 font-semibold' : 'hover:bg-slate-50'
                    }`}>
                      <td className="py-1.5 px-2 text-slate-700">
                        {row.ay_adi}
                        {row.ay === LANSMAN_AY && (
                          <span className="ml-1 text-xs bg-green-600 text-white px-1 rounded">LANSMAN</span>
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-right font-bold text-slate-800 font-mono">
                        {row.hedef.toLocaleString('tr')}
                      </td>
                      <td className="py-1.5 px-2 text-right text-slate-500 font-mono">
                        %{row.pay_pct.toFixed(1)}
                      </td>
                      <td className="py-1.5 px-2 text-right text-slate-500 font-mono">
                        {row.si.toFixed(3)}
                        {row.lansman_boost > 1 && (
                          <span className="text-green-600"> ×{row.lansman_boost}</span>
                        )}
                      </td>
                      <td className="py-1.5 px-2">
                        <div className="w-24 bg-slate-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${row.ay >= LANSMAN_AY ? 'bg-blue-500' : 'bg-slate-400'}`}
                            style={{ width: `${Math.min(100, row.pay_pct * 7)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 bg-slate-50 font-bold">
                    <td className="py-2 px-2 text-slate-800">TOPLAM</td>
                    <td className="py-2 px-2 text-right text-blue-700 font-mono">
                      {ozet.yillik_hedef.toLocaleString('tr')}
                    </td>
                    <td className="py-2 px-2 text-right text-slate-600 font-mono">%100</td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>

          {/* Metodoloji */}
          <MetodolojiBlogu maddeler={metodoloji} />

          {/* Ocak 2026 Bayi Dağılımı */}
          <Card title={`Ocak 2026 Bayi Dağılımı (Toplam: ${ocakToplam} araç)`}>
            <div className="mb-4">
              <BilgiKutusu baslik="Dağıtım Yöntemi" renk="blue">
                <p>
                  <strong>%50 Son 12 ay satış payı</strong> (Ara 2024 – Kas 2025):
                  En güçlü geçmiş performansı olan bayilere daha fazla araç.
                </p>
                <p>
                  <strong>%30 Ocak 2026 resmi hedef payı</strong>:
                  Distribütörün belirlediği resmi bayi hedefleri baz alındı.
                </p>
                <p>
                  <strong>%20 Performans skoru</strong>:
                  2025 yılı boyunca hedef gerçekleştirme oranı (normalized 0–1).
                  Tutarlı yüksek performans gösteren bayiler öne çıkıyor.
                </p>
                <p>
                  <strong>Güven seviyesi</strong>:
                  Yüksek = atama/resmi hedef oranı 0.8–1.25 · Orta = 0.6–1.5 · Düşük = dışında.
                </p>
              </BilgiKutusu>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 font-medium text-slate-500">Bayi</th>
                    <th className="text-center py-2 px-2 font-medium text-slate-500">Tier</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Adet</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Pay%</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Jan26 Hedef</th>
                    <th className="text-right py-2 px-2 font-medium text-slate-500">Perf.</th>
                    <th className="text-center py-2 px-2 font-medium text-slate-500">Güven</th>
                    <th className="text-left py-2 px-3 font-medium text-slate-500">Son 6 Ay Mix</th>
                  </tr>
                </thead>
                <tbody>
                  {ocak_bayi_dagilim.map(row => (
                    <tr key={row.dealer} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="py-1.5 px-2 font-medium text-slate-700">{row.dealer}</td>
                      <td className="py-1.5 px-2 text-center"><TierBadge tier={row.tier} /></td>
                      <td className="py-1.5 px-2 text-right font-mono font-bold text-blue-700">{row.adet}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-slate-500">
                        {row.pay_pct.toFixed(1)}%
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-slate-500">{row.jan26_hedef}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-slate-500">
                        {(row.perf_skoru * 100).toFixed(0)}%
                      </td>
                      <td className="py-1.5 px-2 text-center"><GercekcilikBadge seviye={row.gercekci_mi} /></td>
                      <td className="py-1.5 px-3"><ModelChips mix={row.model_mix} /></td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-slate-300 bg-slate-50 font-bold">
                    <td className="py-2 px-2 text-slate-800">TOPLAM</td>
                    <td />
                    <td className="py-2 px-2 text-right font-mono text-blue-700">{ocakToplam}</td>
                    <td className="py-2 px-2 text-right font-mono text-slate-600">%100</td>
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
          </Card>
        </div>
      )}

      {subTab === 1 && model_aylik && (
        <AylikModelTablosu
          modelAylik={model_aylik}
          yillikHedef={ozet.yillik_hedef}
          lansman_ay={LANSMAN_AY}
        />
      )}
    </div>
  )
}

function Plan2026Tab({ data }: { data: Plan2026 }) {
  const [aktifSenaryo, setAktifSenaryo] = useState<8500 | 10000>(8500)
  const senaryo = aktifSenaryo === 8500 ? data.senaryo_8500 : data.senaryo_10000
  const s8  = data.senaryo_8500.ozet
  const s10 = data.senaryo_10000.ozet

  return (
    <div className="space-y-5">
      {/* Bağlam açıklaması */}
      <BilgiKutusu baslik="Bu Sekme: 2026 Yıllık Araç Dağıtım Planı" renk="slate">
        <p>
          <strong className="text-white">Amaç:</strong>{' '}
          2026 yılı için aylık araç dağıtım hedeflerini belirlemek.
          İki farklı büyüme senaryosu (8500 ve 10000 araç) sunulmaktadır.
          Her senaryo için: (1) aylık toplam hedef, (2) bayi bazında Ocak dağıtımı,
          (3) aylık × model bazında hedef tablosu hesaplanmıştır.
        </p>
        <p>
          <strong className="text-white">Temel Araç — Seasonal Index (SI):</strong>{' '}
          outputs/seasonality/04_FINAL_si.csv dosyasındaki SI değerleri, piyasa geneli otomobil
          mevsimselliği ve marka verisinin ağırlıklı ortalamasından türetildi.
          Ocak SI ≈ 0.66 (yılın en zayıf ayı), Aralık SI ≈ 1.62 (yılın en güçlü ayı).
          Yıllık hedef, bu SI oranlarıyla 12 aya dağıtıldı.
        </p>
        <p>
          <strong className="text-white">Mart Lansman Boostı:</strong>{' '}
          Mart ve sonrası için SI ×1.15 uygulandı. Yeni A1 modelinin tam lansmanı Mart 2026'da.
          Bu boost distribütörün satış stratejisini ve lansman dönemindeki talep artışını yansıtır.
        </p>
        <p>
          <strong className="text-white">Senaryo Seçimi:</strong>{' '}
          8500 → mevcut 2024-2025 büyüme trendini sürdürür (muhafazakâr).
          10000 → A1 lansmanı ve pazar genişlemesiyle agresif büyüme (+%18).
        </p>
      </BilgiKutusu>

      {/* Senaryo seçici */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
          2026 Hedef Senaryosu Seçin
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {([8500, 10000] as const).map(h => {
            const s = h === 8500 ? s8 : s10
            return (
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
                <p className="text-xs text-slate-500 mb-2">
                  {h === 8500
                    ? 'Mevcut büyüme trendi · Muhafazakâr büyüme'
                    : `Agresif büyüme (~+%${Math.round((10000 / 8500 - 1) * 100)}) · A1 tam kapasiteye ulaşır`}
                </p>
                <div className="grid grid-cols-4 gap-1 text-center">
                  {(h === 8500 ? data.senaryo_8500 : data.senaryo_10000).aylik
                    .filter(r => [1, 3, 6, 12].includes(r.ay))
                    .map(r => (
                      <div key={r.ay} className="bg-white rounded border border-slate-200 p-1">
                        <p className="text-xs text-slate-400">{r.ay_adi}</p>
                        <p className="text-sm font-bold text-slate-700">{r.hedef}</p>
                      </div>
                    ))}
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Ocak: <strong>{s.ocak_hedef}</strong> araç (SI bazlı, sabit değil)
                </p>
              </button>
            )
          })}
        </div>
      </div>

      <SenaryoView
        senaryo={senaryo}
        metodoloji={data.metodoloji}
        stratejikBaglam={data.stratejik_baglamlar}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sekme 3: Bayi Bazlı Hedefler (Oca–Ara)
// ---------------------------------------------------------------------------

const SEGMENT_MODELLER: Record<string, string[]> = {
  A: ['A1', 'A2', 'A3'],
  B: ['B1', 'B2'],
  C: ['C1'],
  D: ['D1'],
}

const SEGMENT_RENK: Record<string, string> = {
  A: 'text-blue-700 bg-blue-50',
  B: 'text-amber-700 bg-amber-50',
  C: 'text-rose-700 bg-rose-50',
  D: 'text-slate-600 bg-slate-100',
}

function BayiHedefleriTab({ data }: {
  data: {
    senaryo_8500: BayiAylikHedefler
    senaryo_10000: BayiAylikHedefler
  }
}) {
  const [aktifSenaryo, setAktifSenaryo] = useState<8500 | 10000>(8500)
  const senaryoData = aktifSenaryo === 8500 ? data.senaryo_8500 : data.senaryo_10000

  const bayiler = Object.keys(senaryoData).sort((a, b) => {
    const aNum = parseInt(a.split(' ').pop() || '0', 10)
    const bNum = parseInt(b.split(' ').pop() || '0', 10)
    return aNum - bNum
  })

  const [secilenBayi, setSecilenBayi] = useState<string>(bayiler[0] ?? '')

  // Senaryo değişince bayiyi reset et
  const bayiHedef: BayiHedef | null = senaryoData[secilenBayi] ?? null

  const BILINEN_MODELLER = ['A1', 'A2', 'A3', 'B1', 'B2', 'C1', 'D1']
  const LANSMAN_AY = 3

  return (
    <div className="space-y-6">
      {/* Açıklama */}
      <BilgiKutusu baslik="Bayi Bazlı Aylık Model Hedefleri — Nasıl Hesaplandı?" renk="blue">
        <p>
          Bu sekmede her bayi için Ocak–Aralık 2026 aylık model bazlı satış hedefleri gösterilmektedir.
        </p>
        <p>
          <strong>Yöntem:</strong> Plan sekmesinde hesaplanan aylık model toplamları, her modelde
          bayi bazındaki tarihsel satış paylarıyla (son 12 ay, 2024-12 ile 2025-11) çarpılarak
          bayi bazına indirgendi.
        </p>
        <p>
          <strong>Segment Notu:</strong> A1/A2/A3 aynı A Segmenti aracının versiyonlarıdır (farklı modeller değil).
          B1/B2 aynı B Segmenti aracının versiyonlarıdır.
        </p>
        <p>
          <strong>Sıfır Hedef:</strong> Bir bayinin modeline ait hedefi 0 ise, o bayi bu modeli
          son 12 ayda hiç satmamış demektir — distribütör onayıyla eklenmesi önerilir.
        </p>
        <p>
          <strong>Yuvarlama Notu:</strong> Her bayi hedefi ayrı ayrı yuvarlandığından, bayi
          toplamları senaryo genel toplamıyla tam olarak örtüşmeyebilir.
        </p>
      </BilgiKutusu>

      {/* Senaryo seçici */}
      <div className="flex gap-2">
        {([8500, 10000] as const).map(h => (
          <button key={h} onClick={() => setAktifSenaryo(h)}
            className={`px-5 py-2 rounded-lg text-sm font-semibold border-2 transition-all ${
              aktifSenaryo === h
                ? 'border-blue-500 bg-blue-50 text-blue-800'
                : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
            }`}
          >
            {h.toLocaleString('tr')} Araç Senaryosu
            {aktifSenaryo === h && (
              <span className="ml-2 text-xs bg-blue-600 text-white px-1.5 py-0.5 rounded-full">Aktif</span>
            )}
          </button>
        ))}
      </div>

      {/* Bayi seçici */}
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Bayi Seçin:</label>
        <select
          value={secilenBayi}
          onChange={e => setSecilenBayi(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {bayiler.map(b => {
            const tier = senaryoData[b]?.tier ?? 'C'
            return (
              <option key={b} value={b}>
                {b} — Tier {tier}
              </option>
            )
          })}
        </select>
        {bayiHedef && (
          <TierBadge tier={bayiHedef.tier} />
        )}
      </div>

      {/* Seçili bayi detay */}
      {bayiHedef && (
        <div className="space-y-5">
          {/* Özet kartlar */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard
              label="Yıllık Toplam"
              value={bayiHedef.yillik_toplam.toLocaleString('tr')}
              sub="araç (2026)"
              colorClass="bg-blue-50 border-blue-200"
            />
            {Object.entries(bayiHedef.yillik_segmentler).sort().map(([seg, adet]) => (
              <MetricCard
                key={seg}
                label={`${seg} Segmenti`}
                value={adet.toLocaleString('tr')}
                sub="araç"
                colorClass={
                  seg === 'A' ? 'bg-blue-50 border-blue-200' :
                  seg === 'B' ? 'bg-amber-50 border-amber-200' :
                  seg === 'C' ? 'bg-rose-50 border-rose-200' :
                  'bg-slate-50 border-slate-200'
                }
              />
            ))}
          </div>

          {/* Aylık × Model Matrisi */}
          <Card title={`${secilenBayi} — 2026 Aylık Model Hedefleri`}>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs border-collapse">
                <thead>
                  {/* Segment grup başlıkları */}
                  <tr className="bg-slate-700 text-white">
                    <th className="text-left py-2 px-3 font-semibold sticky left-0 bg-slate-700 z-10 min-w-[90px]" rowSpan={2}>
                      Ay
                    </th>
                    <th className="text-right py-2 px-3 font-semibold min-w-[70px] border-r border-slate-500" rowSpan={2}>
                      Toplam
                    </th>
                    <th className="text-center py-2 px-3 font-semibold border-r border-slate-500 bg-blue-800" colSpan={3}>
                      A Segmenti
                    </th>
                    <th className="text-center py-2 px-3 font-semibold border-r border-slate-500 bg-amber-800" colSpan={2}>
                      B Segmenti
                    </th>
                    <th className="text-center py-2 px-3 font-semibold border-r border-slate-500 bg-rose-800" colSpan={1}>
                      C Segmenti
                    </th>
                    <th className="text-center py-2 px-3 font-semibold bg-slate-600" colSpan={1}>
                      D Segmenti
                    </th>
                  </tr>
                  <tr className="bg-slate-800 text-white">
                    {BILINEN_MODELLER.map((m, i) => {
                      const seg = m[0]
                      const isLastInSeg = i === BILINEN_MODELLER.length - 1
                        || BILINEN_MODELLER[i + 1]?.[0] !== seg
                      return (
                        <th key={m}
                          className={`text-right py-2 px-3 font-semibold min-w-[65px] ${
                            isLastInSeg ? 'border-r border-slate-600' : ''
                          } ${MODEL_COLORS[m] ? '' : ''}`}
                        >
                          <span className={`px-1.5 py-0.5 rounded text-xs ${MODEL_COLORS[m] ?? 'bg-slate-600 text-white'}`}>
                            {m}
                          </span>
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody>
                  {bayiHedef.aylik.map((ayRow, idx) => {
                    const isLansman = ayRow.ay === LANSMAN_AY
                    return (
                      <tr key={ayRow.ay}
                        className={`border-b border-slate-100 ${
                          isLansman ? 'bg-green-50 font-semibold' :
                          idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/40'
                        }`}
                      >
                        <td className={`py-2 px-3 sticky left-0 z-10 font-semibold ${
                          isLansman ? 'bg-green-50 text-green-800' : 'bg-inherit text-slate-700'
                        }`}>
                          <div className="flex items-center gap-1">
                            {ayRow.ay_adi}
                            {isLansman && (
                              <span className="text-xs bg-green-600 text-white px-1 rounded">LANSMAN</span>
                            )}
                          </div>
                        </td>
                        <td className={`py-2 px-3 text-right font-bold border-r border-slate-200 ${
                          isLansman ? 'text-green-800' : 'text-slate-800'
                        }`}>
                          {ayRow.toplam.toLocaleString('tr')}
                        </td>
                        {BILINEN_MODELLER.map((m, i) => {
                          const adet = ayRow.modeller[m] ?? 0
                          const seg = m[0]
                          const isLastInSeg = i === BILINEN_MODELLER.length - 1
                            || BILINEN_MODELLER[i + 1]?.[0] !== seg
                          const isNoSale = adet === 0
                          return (
                            <td key={m}
                              className={`py-2 px-3 text-right font-mono ${
                                isLastInSeg ? 'border-r border-slate-200' : ''
                              } ${
                                isNoSale ? 'text-slate-300' :
                                m === 'B1' ? 'text-amber-700 font-semibold' :
                                m.startsWith('A') ? 'text-blue-700' :
                                m === 'C1' ? 'text-rose-700' :
                                'text-slate-600'
                              }`}
                              title={isNoSale ? 'Bu bayi bu modeli tarihsel olarak satmamıştır — distribütör onayıyla eklenmeli' : undefined}
                            >
                              {adet > 0 ? adet.toLocaleString('tr') : '—'}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-100 font-bold border-t-2 border-slate-300">
                    <td className="py-3 px-3 text-slate-800 sticky left-0 bg-slate-100">YIL TOPLAMI</td>
                    <td className="py-3 px-3 text-right text-blue-700 border-r border-slate-300 font-mono">
                      {bayiHedef.yillik_toplam.toLocaleString('tr')}
                    </td>
                    {BILINEN_MODELLER.map((m, i) => {
                      const adet = bayiHedef.yillik_modeller[m] ?? 0
                      const seg = m[0]
                      const isLastInSeg = i === BILINEN_MODELLER.length - 1
                        || BILINEN_MODELLER[i + 1]?.[0] !== seg
                      return (
                        <td key={m}
                          className={`py-3 px-3 text-right font-mono ${
                            isLastInSeg ? 'border-r border-slate-300' : ''
                          } ${adet === 0 ? 'text-slate-300' : 'text-slate-700'}`}
                        >
                          {adet > 0 ? adet.toLocaleString('tr') : '—'}
                          {adet > 0 && bayiHedef.yillik_toplam > 0 && (
                            <span className="block text-xs font-normal text-slate-400">
                              %{((adet / bayiHedef.yillik_toplam) * 100).toFixed(1)}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                  {/* Segment toplamları */}
                  <tr className="bg-slate-50 border-t border-slate-200 text-xs">
                    <td className="py-2 px-3 text-slate-500 sticky left-0 bg-slate-50 italic">Seg. Toplamı</td>
                    <td className="py-2 px-3 border-r border-slate-200" />
                    {BILINEN_MODELLER.map((m, i) => {
                      const seg = m[0]
                      const segToplam = bayiHedef.yillik_segmentler[seg] ?? 0
                      const isLastInSeg = i === BILINEN_MODELLER.length - 1
                        || BILINEN_MODELLER[i + 1]?.[0] !== seg
                      // Sadece her segmentin son sütununda segment toplam göster
                      const segModels = SEGMENT_MODELLER[seg] ?? []
                      const isFirstInSeg = m === segModels[0]
                      return (
                        <td key={m}
                          className={`py-2 px-3 text-center font-semibold ${
                            isLastInSeg ? 'border-r border-slate-200' : ''
                          } ${SEGMENT_RENK[seg] ?? 'text-slate-600'}`}
                          colSpan={isFirstInSeg ? segModels.length : undefined}
                          style={!isFirstInSeg ? { display: 'none' } : undefined}
                        >
                          {isFirstInSeg ? `${segToplam.toLocaleString('tr')} araç` : ''}
                        </td>
                      )
                    })}
                  </tr>
                </tfoot>
              </table>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              — = bu bayi bu modeli tarihsel olarak satmamıştır (0 hedef) ·
              LANSMAN = Mart 2026 (×1.15 boost uygulandı) ·
              Yuvarlama nedeniyle toplam tam eşleşmeyebilir
            </p>
          </Card>
        </div>
      )}

      {/* Tüm bayiler özet tablosu */}
      <Card title="Tüm Bayiler Özet — Yıllık Hedefler">
        <p className="text-xs text-slate-500 mb-3">
          Bir bayiye tıklayarak yukarıdaki detay tablosunu görüntüleyebilirsiniz.
          Yuvarlama nedeniyle bayi toplamları senaryo genel toplamına tam eşit gelmeyebilir.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left py-2 px-2 font-semibold text-slate-600">Bayi</th>
                <th className="text-center py-2 px-2 font-semibold text-slate-600">Tier</th>
                <th className="text-right py-2 px-2 font-semibold text-slate-600">Yıllık</th>
                <th className="text-right py-2 px-2 font-semibold text-blue-700">A Seg.</th>
                <th className="text-right py-2 px-2 font-semibold text-amber-700">B Seg.</th>
                <th className="text-right py-2 px-2 font-semibold text-rose-700">C Seg.</th>
                <th className="text-right py-2 px-2 font-semibold text-slate-500">Ocak</th>
                <th className="text-right py-2 px-2 font-semibold text-slate-500">Şubat</th>
                <th className="text-right py-2 px-2 font-semibold text-green-700">Mart ✦</th>
              </tr>
            </thead>
            <tbody>
              {bayiler.map(bayi => {
                const bh = senaryoData[bayi]
                if (!bh) return null
                const ocak = bh.aylik.find(a => a.ay === 1)?.toplam ?? 0
                const subat = bh.aylik.find(a => a.ay === 2)?.toplam ?? 0
                const mart = bh.aylik.find(a => a.ay === 3)?.toplam ?? 0
                const isSecili = bayi === secilenBayi
                return (
                  <tr key={bayi}
                    onClick={() => setSecilenBayi(bayi)}
                    className={`border-b border-slate-100 cursor-pointer transition-colors ${
                      isSecili ? 'bg-blue-50' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className={`py-1.5 px-2 font-medium ${isSecili ? 'text-blue-700' : 'text-slate-700'}`}>
                      {bayi}
                    </td>
                    <td className="py-1.5 px-2 text-center">
                      <TierBadge tier={bh.tier} />
                    </td>
                    <td className="py-1.5 px-2 text-right font-bold font-mono text-slate-800">
                      {bh.yillik_toplam.toLocaleString('tr')}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono text-blue-700">
                      {(bh.yillik_segmentler['A'] ?? 0).toLocaleString('tr')}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono text-amber-700">
                      {(bh.yillik_segmentler['B'] ?? 0).toLocaleString('tr')}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono text-rose-700">
                      {(bh.yillik_segmentler['C'] ?? 0).toLocaleString('tr')}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono text-slate-500">{ocak}</td>
                    <td className="py-1.5 px-2 text-right font-mono text-slate-500">{subat}</td>
                    <td className="py-1.5 px-2 text-right font-mono font-semibold text-green-700">{mart}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-300 bg-slate-100 font-bold">
                <td className="py-2 px-2 text-slate-800" colSpan={2}>TOPLAM</td>
                <td className="py-2 px-2 text-right font-mono text-blue-700">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_toplam ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-blue-700">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_segmentler['A'] ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-amber-700">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_segmentler['B'] ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-rose-700">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_segmentler['C'] ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-slate-500">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 1)?.toplam ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-slate-500">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 2)?.toplam ?? 0), 0).toLocaleString('tr')}
                </td>
                <td className="py-2 px-2 text-right font-mono text-green-700">
                  {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 3)?.toplam ?? 0), 0).toLocaleString('tr')}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          ✦ Mart = Lansman ayı (×1.15 boost) · Satıra tıklayarak bayi detayını görüntüleyin
        </p>
      </Card>
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
          Aralık 2025 tier bazlı geriye dönük doğrulama · 2026 yıllık plan (8500 / 10000 araç) · Ocak–Aralık model bazlı hedefler · Bayi bazlı aylık hedefler
        </p>
      </div>

      <TabBar
        tabs={['Aralık 2025 Tahmini', '2026 Yıllık Plan & Model Hedefleri', 'Bayi Bazlı Hedefler (Oca–Ara)']}
        active={tab}
        onChange={setTab}
      />

      {tab === 0 && <AralikTab data={data.aralik_tahmin} />}
      {tab === 1 && <Plan2026Tab data={data.plan_2026} />}
      {tab === 2 && data.bayi_aylik_hedefler && (
        <BayiHedefleriTab data={data.bayi_aylik_hedefler} />
      )}
    </div>
  )
}
