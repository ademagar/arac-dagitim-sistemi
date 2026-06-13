import { useState } from 'react'
import {
  BookOpen, ChevronDown, ChevronRight, Database, BarChart2, TrendingUp,
  Target, Truck, Map, Calendar, GitBranch, Layers, Cpu, FileText,
  CheckCircle, AlertCircle, Zap, Settings, Globe, Code2, ArrowRight,
  Users, Activity
} from 'lucide-react'

/* ─── Yardımcı bileşenler ─────────────────────────────── */

function SectionHeader({ icon: Icon, title, subtitle, color = 'blue' }: {
  icon: React.ElementType, title: string, subtitle: string, color?: string
}) {
  const colorMap: Record<string, string> = {
    blue:   'from-blue-500/20 to-blue-600/5 border-blue-500/30 text-blue-400',
    violet: 'from-violet-500/20 to-violet-600/5 border-violet-500/30 text-violet-400',
    emerald:'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30 text-emerald-400',
    amber:  'from-amber-500/20 to-amber-600/5 border-amber-500/30 text-amber-400',
    rose:   'from-rose-500/20 to-rose-600/5 border-rose-500/30 text-rose-400',
    sky:    'from-sky-500/20 to-sky-600/5 border-sky-500/30 text-sky-400',
    teal:   'from-teal-500/20 to-teal-600/5 border-teal-500/30 text-teal-400',
    indigo: 'from-indigo-500/20 to-indigo-600/5 border-indigo-500/30 text-indigo-400',
  }
  const cls = colorMap[color] ?? colorMap['blue']
  return (
    <div className={`bg-gradient-to-r ${cls} border rounded-2xl px-6 py-5 mb-6 flex items-center gap-4`}>
      <div className={`p-3 rounded-xl bg-slate-800/80`}>
        <Icon size={24} className={cls.split(' ')[3]} />
      </div>
      <div>
        <h2 className="text-white text-xl font-bold">{title}</h2>
        <p className="text-slate-200 text-sm mt-0.5">{subtitle}</p>
      </div>
    </div>
  )
}

function AkademikBadge({ label }: { label: string }) {
  return (
    <span className="inline-block bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs font-bold px-2.5 py-0.5 rounded-full mr-1.5 mb-1">
      {label}
    </span>
  )
}

function InfoCard({ title, children, color = 'slate' }: { title: string, children: React.ReactNode, color?: string }) {
  const bg: Record<string,string> = {
    slate:  'bg-slate-800/60 border-slate-700/50',
    blue:   'bg-blue-950/40 border-blue-800/40',
    violet: 'bg-violet-950/40 border-violet-800/40',
    emerald:'bg-emerald-950/40 border-emerald-800/40',
    amber:  'bg-amber-950/40 border-amber-800/40',
    rose:   'bg-rose-950/40 border-rose-800/40',
  }
  return (
    <div className={`${bg[color] ?? bg.slate} border rounded-xl p-5`}>
      <h4 className="text-white font-semibold text-sm mb-3">{title}</h4>
      {children}
    </div>
  )
}

function FormulSatir({ label, formula, aciklama }: { label: string, formula: string, aciklama: string }) {
  return (
    <div className="mb-4 last:mb-0">
      <p className="text-slate-200 text-xs mb-1">{label}</p>
      <code className="block bg-slate-900/70 border border-slate-700/50 rounded-lg px-4 py-2.5 text-emerald-400 font-mono text-xs mb-1.5 leading-relaxed overflow-x-auto whitespace-pre-wrap break-words">
        {formula}
      </code>
      <p className="text-slate-200 text-xs leading-relaxed pl-1">{aciklama}</p>
    </div>
  )
}

function Accordion({ title, icon: Icon, defaultOpen = false, children }: {
  title: string, icon: React.ElementType, defaultOpen?: boolean, children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl mb-3 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-700/30 transition-colors"
      >
        <Icon size={17} className="text-slate-200 flex-shrink-0" />
        <span className="text-white font-semibold text-sm flex-1">{title}</span>
        {open ? <ChevronDown size={16} className="text-slate-200" /> : <ChevronRight size={16} className="text-slate-200" />}
      </button>
      {open && <div className="px-5 pb-5 pt-1">{children}</div>}
    </div>
  )
}

function StepBadge({ num }: { num: number }) {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold mr-2 flex-shrink-0">
      {num}
    </span>
  )
}

/* ─── Ana sayfa ───────────────────────────────────────── */

export default function Ozet() {
  return (
    <div className="max-w-5xl mx-auto pb-16 space-y-12 bg-slate-950 rounded-2xl p-6 -m-2 min-h-screen">

      {/* ── Hero ── */}
      <div className="relative bg-gradient-to-br from-slate-900 via-blue-950/40 to-slate-900 border border-blue-900/40 rounded-3xl px-8 py-10 overflow-hidden">
        <div className="absolute inset-0 opacity-5" style={{
          backgroundImage: 'repeating-linear-gradient(0deg,transparent,transparent 40px,#4a90d9 40px,#4a90d9 41px),repeating-linear-gradient(90deg,transparent,transparent 40px,#4a90d9 40px,#4a90d9 41px)'
        }} />
        <div className="relative">
          <div className="flex flex-wrap gap-2 mb-4">
            <AkademikBadge label="Vehicle Allocation Problem" />
            <AkademikBadge label="MCDM" />
            <AkademikBadge label="MILP" />
            <AkademikBadge label="Hierarchical Time Series" />
            <AkademikBadge label="Collaborative Filtering" />
            <AkademikBadge label="Assortment Optimization" />
          </div>
          <h1 className="text-3xl font-black text-white leading-tight mb-3">
            Otomotiv Bayi Satış Destek Sistemi
          </h1>
          <p className="text-white text-base leading-relaxed max-w-3xl">
            Bir otomotiv markasının SUV segmentindeki araçlarını, 28 bayiye adil ve veri odaklı biçimde
            dağıtmayı otomatize eden, Endüstri Mühendisliği bitirme tezi kapsamında geliştirilen karar destek sistemi.
            2026 Ocak itibarıyla aylık çalışacak şekilde tasarlanmıştır.
          </p>
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { val: '28', lbl: 'Bayi' },
              { val: '10.000', lbl: '2026 Araç Hedefi' },
              { val: '7', lbl: 'Modül' },
              { val: '12', lbl: 'Aylık Döngü' },
            ].map(({ val, lbl }) => (
              <div key={lbl} className="bg-slate-800/60 rounded-xl px-4 py-3 text-center">
                <p className="text-2xl font-black text-blue-400">{val}</p>
                <p className="text-slate-200 text-xs mt-0.5">{lbl}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── 1. Problem Tanımı ── */}
      <section>
        <SectionHeader icon={BookOpen} title="1. Problem Tanımı ve Akademik Çerçeve" subtitle="Neden bu problemi çözüyoruz, literatürdeki yeri nedir?" color="blue" />
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <InfoCard title="Vehicle Allocation Problem (VAP)" color="blue">
            <p className="text-white text-sm leading-relaxed">
              VAP, kısıtlı sayıda birbirinden farklı ürünü (araçları) birden çok lokasyona (bayilere) atama
              problemidir. Klasik atama probleminin genelleştirilmiş hali olup NP-Hard kategorisindedir.
              Burada;
            </p>
            <ul className="mt-2 space-y-1 text-white text-sm">
              <li className="flex items-start gap-2"><ArrowRight size={13} className="text-blue-400 mt-0.5 flex-shrink-0" />Ürünler: model × versiyon × renk kombinasyonları</li>
              <li className="flex items-start gap-2"><ArrowRight size={13} className="text-blue-400 mt-0.5 flex-shrink-0" />Lokasyonlar: 28 bayi</li>
              <li className="flex items-start gap-2"><ArrowRight size={13} className="text-blue-400 mt-0.5 flex-shrink-0" />Kısıt: Aylık toplam envanter (300–1500 araç)</li>
            </ul>
          </InfoCard>
          <InfoCard title="Neden otomasyona ihtiyaç var?" color="violet">
            <p className="text-white text-sm leading-relaxed">
              Manuel dağıtımda üst yönetim kararları kişisel deneyime dayanır; sezgisel kararlar çoğunlukla
              yüksek satış potansiyelli bayilerin göz ardı edilmesine ya da stok dengesizliğine yol açar.
              Sistemimiz şu soruları yanıtlar:
            </p>
            <ul className="mt-2 space-y-1 text-white text-sm">
              <li className="flex items-start gap-2"><CheckCircle size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />Hangi bayiye kaç araç verilmeli?</li>
              <li className="flex items-start gap-2"><CheckCircle size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />Hangi model/renk kombinasyonu o bayiye uygun?</li>
              <li className="flex items-start gap-2"><CheckCircle size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />Yıllık hedefe yakın kalınıyor mu?</li>
            </ul>
          </InfoCard>
        </div>
        <InfoCard title="Akademik kavramların sistemdeki karşılıkları" color="slate">
          <div className="grid md:grid-cols-3 gap-3">
            {[
              { kavram: 'MCDM', aciklama: 'Bayi bazında 4 kriter (performans, lokasyon uyumu, mevsimsellik, hedef yakınlığı) ağırlıklı olarak bir skor üretir. Bu skor pazar payı hedefini belirler.' },
              { kavram: 'MILP', aciklama: 'Araç atama adımında PuLP + CBC solver kullanılır. Karar değişkeni: x[araç][bayi] ∈ {0,1}. Amaç fonksiyonu hedef sapmayı minimize eder.' },
              { kavram: 'Collaborative Filtering', aciklama: 'Bayi–model uyum skoru, cosine similarity ile bayilerin geçmiş satış profilleri arasındaki benzerlik hesaplanarak türetilir; öneri sistemlerinden uyarlanmıştır.' },
              { kavram: 'Hierarchical Time Series', aciklama: 'Toplam pazar tahmini önce yapılır, ardından bayi bazına dağıtılır. Bu hiyerarşik yapı tahminlerin tutarlı toplanmasını (reconciliation) sağlar.' },
              { kavram: 'STL Decomposition', aciklama: 'Satış serisini Trend + Seasonal + Residual bileşenlerine ayırır. Her bayinin mevsimsel indeksi ayrı hesaplanır; bu skor dağıtımda kullanılır.' },
              { kavram: 'Assortment Optimization', aciklama: 'Sadece kaç araç değil, hangi karışım (model/renk/versiyon) atanacağı da optimize edilir. Bayinin geçmiş profil vektörüne yakınlık soft constraint olarak eklenir.' },
            ].map(({ kavram, aciklama }) => (
              <div key={kavram} className="bg-slate-900/60 rounded-xl p-4">
                <p className="text-amber-300 font-bold text-sm mb-1.5">{kavram}</p>
                <p className="text-slate-200 text-xs leading-relaxed">{aciklama}</p>
              </div>
            ))}
          </div>
        </InfoCard>
      </section>

      {/* ── 2. Veri Katmanı ── */}
      <section>
        <SectionHeader icon={Database} title="2. Veri Katmanı" subtitle="Hangi veriler kullanılıyor, nasıl yapılandırıldı?" color="emerald" />
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <InfoCard title="CSV Dosyaları (data/raw/)" color="emerald">
            {[
              { dosya: 'sales_2024_2025.csv', icerik: 'Geçmiş satışlar – bayi × model × versiyon × renk × tarih' },
              { dosya: 'dealer_targets_2026.csv', icerik: '28 bayinin 2026 yıllık araç hedefi' },
              { dosya: 'dealer_locations.csv', icerik: 'Bayi il/ilçe, enlem/boylam bilgisi' },
              { dosya: 'monthly_performance_2025.csv', icerik: '2025 aylık hedef, gerçekleşme, yüzde' },
              { dosya: 'competitor_sales.csv', icerik: 'Rakip marka il bazında satışları (upper mainstream)' },
              { dosya: 'inventory_2026_0X.csv', icerik: 'Her ay gönderilecek araç havuzu (CENT-STOCK, Dispatchable=Y)' },
            ].map(({ dosya, icerik }) => (
              <div key={dosya} className="flex items-start gap-2 py-2 border-b border-slate-700/40 last:border-0">
                <FileText size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                <div>
                  <code className="text-emerald-300 text-xs font-mono">{dosya}</code>
                  <p className="text-slate-200 text-xs mt-0.5">{icerik}</p>
                </div>
              </div>
            ))}
          </InfoCard>
          <InfoCard title="SQLite Şeması (arac_dagitim.db)" color="slate">
            <p className="text-slate-200 text-xs mb-3">
              CSV'lerden türetilen normalize edilmiş ilişkisel şema. Boyut tabloları (dim_) ve
              olgu tabloları (fact_) ayrımı yapılmıştır; star schema mimarisi.
            </p>
            {[
              { tablo: 'dim_bayi', alan: 'bayi_id, bayi_adi, il, ilce, lat, lon' },
              { tablo: 'dim_arac', alan: 'arac_id, model, versiyon, renk, grup' },
              { tablo: 'fact_satis', alan: 'bayi_id, arac_id, tarih, adet' },
              { tablo: 'fact_hedef', alan: 'bayi_id, ay, hedef, gerceklesme, yuzde' },
              { tablo: 'fact_envanter', alan: 'arac_id, ay_yil, adet, dispatchable' },
              { tablo: 'dim_rakip_satis', alan: 'il, ay_yil, marka, adet' },
            ].map(({ tablo, alan }) => (
              <div key={tablo} className="flex items-start gap-2 py-1.5 border-b border-slate-700/40 last:border-0">
                <code className="text-sky-300 text-xs font-mono w-28 flex-shrink-0 break-all">{tablo}</code>
                <code className="text-slate-200 text-xs font-mono leading-relaxed break-words">{alan}</code>
              </div>
            ))}
          </InfoCard>
        </div>
        <InfoCard title="Neden anonimleştirme yapıldı?" color="amber">
          <p className="text-white text-sm leading-relaxed">
            Gerçek bayi isimleri ticari sır kapsamındadır. Tüm bayiler "Bayi 01" – "Bayi 30" formatına
            dönüştürülmüş; marka adı kodda parametrik tutulmuştur (<code className="text-amber-300 text-xs">config.py → BRAND_NAME</code>).
            Dashboard'da <code className="text-amber-300 text-xs">DEMO_MODE=True</code> ile çalışır. Bu yaklaşım hem
            KVKK uyumluluğu hem de akademik yayında kullanılabilirlik açısından zorunludur.
          </p>
        </InfoCard>
      </section>

      {/* ── 3. Pazar Hedefleri Modülü ── */}
      <section>
        <SectionHeader icon={Target} title="3. Pazar Hedefleri Modülü" subtitle="Bayinin 2026 pazar payı hedefi nasıl hesaplanıyor?" color="violet" />
        <div className="space-y-3">
          <Accordion title="Formül ve matematiksel arka plan" icon={Code2} defaultOpen>
            <div className="mb-4 bg-blue-950/40 border border-blue-800/40 rounded-xl px-4 py-3">
              <p className="text-blue-200 text-xs font-semibold mb-1">Yöntem</p>
              <p className="text-white text-xs leading-relaxed">
                Hibrit Pazar Payı Formülü — MCDM çerçevesinde <span className="text-amber-300 font-semibold">iki kriter</span>:{' '}
                <span className="text-emerald-300">%50 geçmiş marka performansı</span> (2025 satış payı) +{' '}
                <span className="text-violet-300">%50 pazar kapasitesi</span> (TÜİK il bazlı araç stoku).
              </p>
            </div>
            <FormulSatir
              label="Bayinin yıllık hedef araç payı:"
              formula={"share_i = 0.50 × SatışPayı_i(2025)\n         + 0.50 × (TÜİKStok_il(i) / BayiSayısı_il(i))"}
              aciklama="SatışPayı: bayinin 2025'te toplam marka satışları içindeki payı. TÜİKStok: bayinin bulunduğu ilde TÜİK verisinden elde edilen il bazlı toplam araç stok çekim alanı. İl kotası o ildeki bayi sayısına eşit bölünür."
            />
            <FormulSatir
              label="Yıllık araç hedefi:"
              formula="Hedef_i = share_i × 10.000   (share toplamı = 1 olacak şekilde normalize edilir)"
              aciklama="Normalizasyon, toplam dağıtılacak araç sayısının her koşulda 10.000'e eşit kalmasını garantiler."
            />
            <div className="mt-3 bg-amber-950/40 border border-amber-700/40 rounded-xl px-4 py-3">
              <p className="text-amber-300 text-xs font-semibold mb-1">Yeni bayi özel kuralı</p>
              <p className="text-white text-xs leading-relaxed">
                2025 satış verisi bulunmayan yeni bayiler için SatışPayı = 0 olur ve formül tamamen
                kapasite bazlı çalışır: <code className="text-emerald-400">share_i = TÜİKStok_il(i) / BayiSayısı_il(i)</code>.
                Bu, yeni bayinin bulunduğu ilin potansiyelini baz alan bir "başlangıç kotası" sağlar.
              </p>
            </div>
          </Accordion>
          <Accordion title="Neden %50 / %50 ağırlık?" icon={Settings}>
            <p className="text-white text-sm leading-relaxed mb-3">
              Tamamen geçmiş performansa dayalı bir ağırlık (α=1), sıfır büyüme varsayımıyla yeni bayileri
              cezalandırır — hiç satışı olmayan yeni bayi sıfır kota alır. Tamamen coğrafi kapasiteye dayalı
              (β=1) ise köklü, yüksek satışlı bayileri görmezden gelir. Eşit ağırlık ikisini dengeler.
            </p>
            <p className="text-slate-200 text-xs">
              Bu parametre <code className="text-emerald-400">config.py</code>'de kolayca değiştirilebilir.
              Gelecekte farklı α/β denemeleri için duyarlılık analizi yapılabilir.
            </p>
          </Accordion>
          <Accordion title="TÜİK il bazlı araç stoku neden kullanıldı?" icon={Activity}>
            <p className="text-white text-sm leading-relaxed mb-3">
              Sadece kendi satış verimize bakarsak yüksek potansiyelli ama düşük kotada bırakılmış
              bayileri tespit edemeyiz. TÜİK'in il bazlı araç stok verisi, bir ilin motorlu taşıt
              "çekim alanını" nesnel biçimde ölçer — satın alma gücü, nüfus yoğunluğu ve otomobil
              sahiplik oranını dolaylı olarak yansıtır.
            </p>
            <p className="text-slate-200 text-xs">
              Bu veri, rakip marka satışlarını da kapsayan üst-ana-akım (upper mainstream) segmentin
              proxy değişkeni olarak modele dahil edilmiştir. Rakip verisi ayrıca <code className="text-emerald-400">competitor_sales.csv</code>'de
              tutulmaktadır.
            </p>
          </Accordion>
        </div>
      </section>

      {/* ── 4. Tahmin Modülü ── */}
      <section>
        <SectionHeader icon={TrendingUp} title="4. Tahmin & Plan Modülü" subtitle="2026 aylık satış tahmini nasıl yapılıyor?" color="sky" />
        <div className="space-y-3">
          <Accordion title="STL Decomposition — neden bu yöntem?" icon={BarChart2} defaultOpen>
            <p className="text-white text-sm leading-relaxed mb-3">
              Otomotiv satışları güçlü bir mevsimsellik içerir (yıl sonu kampanyaları, plaka değişimi).
              STL (Seasonal-Trend decomposition using Loess), bu mevsimselliği trend'den temizleyerek
              ayrı ayrı modellenebilir bileşenler üretir:
            </p>
            <code className="block bg-slate-900 border border-slate-700/50 rounded-lg px-4 py-2.5 text-emerald-400 font-mono text-xs mb-4 text-center tracking-wide">
              Satış = Trend × Mevsimsellik × Kalıntı
            </code>
            <div className="space-y-3">
              <div className="bg-slate-900/60 border border-slate-700/30 rounded-xl p-4">
                <p className="text-sky-300 text-sm font-bold mb-1">Trend (T)</p>
                <p className="text-white text-xs leading-relaxed">
                  Satış serisinin uzun dönem yönü. Otomotiv pazarında ekonomik büyüme, nüfus artışı ve
                  markanın pazar payı değişimini yansıtır. Örneğin 2024→2025 arasında pazar %8 büyüdüyse
                  trend bileşeni bunu yakalar.
                </p>
              </div>
              <div className="bg-slate-900/60 border border-slate-700/30 rounded-xl p-4">
                <p className="text-sky-300 text-sm font-bold mb-1">Mevsimsellik (S)</p>
                <p className="text-white text-xs leading-relaxed mb-2">
                  Her yıl aynı aylarda tekrar eden örüntüler. Türkiye otomotiv pazarında Ocak–Şubat
                  düşük, Mart–Nisan ve Ekim–Kasım yüksek satış dönemleridir (plaka sonu, kampanya
                  dönemleri). Her bayi için ayrı bir Seasonal Index (SI) hesaplanır:
                </p>
                <code className="block bg-slate-950 rounded-lg px-3 py-2 text-emerald-400 font-mono text-xs">
                  SI_i_ay = (Bayinin o aydaki ortalama satışı) / (Bayinin yıllık ortalama aylık satışı)
                </code>
                <p className="text-slate-200 text-xs mt-2">
                  SI {'>'} 1 → o ay bayi için iyi bir ay · SI {'<'} 1 → zayıf bir ay
                </p>
              </div>
              <div className="bg-slate-900/60 border border-slate-700/30 rounded-xl p-4">
                <p className="text-sky-300 text-sm font-bold mb-1">Kalıntı / Artık (R)</p>
                <p className="text-white text-xs leading-relaxed mb-2">
                  Trend ve mevsimsellik çıkarıldıktan sonra geriye kalan açıklanamayan varyasyon.
                  Kalıntı = Gerçek Satış / (Trend × Mevsimsellik) formülüyle hesaplanır.
                  Kalıntı bileşeni iki şeyi temsil eder:
                </p>
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-400 font-bold text-xs mt-0.5 flex-shrink-0">1.</span>
                    <p className="text-white text-xs leading-relaxed">
                      <span className="text-amber-300 font-semibold">Gerçek rassal şoklar:</span> Ani
                      ekonomik kriz, yakıt fiyatı artışı, COVID gibi öngörülemeyen dış olaylar.
                      Bu kısım modelin kontrol edemeyeceği gürültüdür.
                    </p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-amber-400 font-bold text-xs mt-0.5 flex-shrink-0">2.</span>
                    <p className="text-white text-xs leading-relaxed">
                      <span className="text-amber-300 font-semibold">Model kalite göstergesi:</span> Kalıntının
                      standart sapması küçükse model veriyi iyi açıklıyor demektir. Büyükse
                      yakalanamamış bir örüntü var demektir (mevsim periyodu yanlış veya başka bir değişken eksik).
                    </p>
                  </div>
                </div>
                <div className="mt-3 bg-slate-950 border border-slate-700/50 rounded-lg px-3 py-2">
                  <p className="text-slate-200 text-xs">
                    <span className="text-white font-semibold">Bu projede kalıntı nasıl kullanılıyor?</span>
                    {' '}Tahmin aşamasında kalıntı görmezden gelinir (sıfır gürültü varsayımı).
                    Ancak kalıntının büyüklüğü model seçimini doğrulamak için izlenir:
                    kalıntı standart sapması toplam varyasyonun %15'inden fazlaysa model
                    gözden geçirilmelidir.
                  </p>
                </div>
              </div>
            </div>
          </Accordion>
          <Accordion title="Prophet — neden STL'e ek olarak?" icon={TrendingUp}>
            <p className="text-white text-sm leading-relaxed">
              STL tek başına gelecek tahmininde güçsüzdür; geriye dönük olarak ayrıştırır, ileriye
              ekstrapolasyon yapmaz. Prophet (Facebook/Meta), dışsal olayları (tatiller, kampanyalar) ve
              doğrusal olmayan trendi modelleyerek 12 aylık projeksiyonu güvenilir biçimde üretir.
              İki yöntemin birlikte kullanılması (Hybrid Forecasting), STL'in doğru mevsimsellik
              tahminini Prophet'in ileri projeksiyon gücüyle birleştirir.
            </p>
          </Accordion>
          <Accordion title="Hiyerarşik yapı — bayiden toplama reconciliation" icon={GitBranch}>
            <p className="text-white text-sm leading-relaxed">
              Önce toplam pazar (28 bayi toplamı) tahmin edilir, ardından bayi bazına indirgenir.
              Bu top-down yaklaşım, alt seviye tahminlerin birbirine eklenmesiyle toplam hedefi
              aşma riskini ortadan kaldırır. Alternatif bottom-up tahmin, bayi başına aşırı
              uyum (overfitting) riskini artırırdı çünkü bazı bayilerin yeterince uzun tarihsel
              serisi yoktur (yeni bayiler).
            </p>
          </Accordion>
          <Accordion title="Lansman boostı (×1.11) nereden geliyor?" icon={Zap}>
            <p className="text-white text-sm leading-relaxed">
              2026, yeni model yılı lansmanını içeriyor. Sektör verilerine göre lansman yılında
              satışlar ortalama %10-15 artış gösteriyor. Sistemde bu, tahmin edilen bazeline
              ×1.11 çarpanı uygulanarak modellendi. Bu katsayı <code className="text-emerald-400 text-xs">config.py</code>'de
              değiştirilebilir şekilde tutulmuştur; gerçek lansman verisine göre kalibre edilmelidir.
            </p>
          </Accordion>
        </div>
      </section>

      {/* ── 5. Aylık Bayi Hedef ── */}
      <section>
        <SectionHeader icon={Calendar} title="5. Aylık Bayi Hedef Modülü" subtitle="MCDM skorlaması ve aylık kota hesabı" color="amber" />
        <div className="space-y-3">
          <Accordion title="4 Kriter ve ağırlıkları" icon={Layers} defaultOpen>
            <div className="grid md:grid-cols-2 gap-3 mb-3">
              {[
                { kriter: 'P — Performans Skoru', agirlik: 'w = 0.25', formul: 'EW ortalama (W=5, α=0.333) → son 5 ay aylık hedef gerçekleştirme oranı', renk: 'text-blue-400', neden: 'Geçmişte yüksek gerçekleşme oranı olan bayi gelecekte de daha fazla araç satar. W=5 yıl bazında en tutarlı pencere: 2024 MAE=10.97 / 2025 MAE=11.93, yıllar arası fark sadece 0.96.' },
                { kriter: 'LP — Lokasyon-Ürün Uyum', agirlik: 'w = 0.35', formul: 'Cosine similarity: bayinin geçmiş model vektörü ile envanter vektörü arası benzerlik', renk: 'text-violet-400', neden: 'En yüksek ağırlık. Bayinin satabileceği modeli gönderiyoruz; yanlış model göndermek stok çürümesine neden olur.' },
                { kriter: 'S — Mevsimsel Uyum', agirlik: 'w = 0.20', formul: 'seasonal_index = (bayi_ay_ort) / (bayi_yıl_ort)', renk: 'text-emerald-400', neden: 'Bazı bayiler yaz aylarında, bazıları kış aylarında daha fazla satar. Yanlış zamanlama, iade veya sıfıra düşen stok demektir.' },
                { kriter: 'H — Hedef Yakınlık', agirlik: 'w = 0.20', formul: 'gecikme = max(0, beklenen_ytd − gerçek_ytd) / yıllık_hedef\nH = 1 + gecikme', renk: 'text-amber-400', neden: 'Asimetrik: hedefin gerisindeki bayi ekstra araç alır (H > 1). Hedefini tutturan ya da geçen bayi ne cezalanır ne ekstra alır (H = 1).' },
              ].map(({ kriter, agirlik, formul, renk, neden }) => (
                <div key={kriter} className="bg-slate-900/60 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-1">
                    <p className={`font-bold text-sm ${renk}`}>{kriter}</p>
                    <span className="bg-slate-700 text-white text-xs px-2 py-0.5 rounded-full font-bold">{agirlik}</span>
                  </div>
                  <code className="block text-xs text-white font-mono mb-2 leading-relaxed overflow-x-auto whitespace-pre-wrap break-words">{formul}</code>
                  <p className="text-slate-200 text-xs leading-relaxed">{neden}</p>
                </div>
              ))}
            </div>
            <div className="bg-slate-900/60 rounded-xl px-4 py-3">
              <p className="text-slate-200 text-xs mb-1">Birleşik skor:</p>
              <code className="block text-emerald-400 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-words">
                Score_i = 0.25×P_i + 0.35×LP_i + 0.20×S_i + 0.20×H_i
              </code>
              <p className="text-slate-200 text-xs mt-2">
                Bu skor, bayinin o ayki "araç alma hakkının" ağırlığını temsil eder. Aylık toplam kota,
                Score_i değerlerine orantılı dağıtılır.
              </p>
            </div>
          </Accordion>
          <Accordion title="EW pencere analizi — W=5 neden seçildi?" icon={TrendingUp} defaultOpen>
            <p className="text-white text-sm leading-relaxed mb-3">
              2024–2025 gerçekleşme verisi (24 ay) üzerinde, W=3'ten W=19'a kadar her pencere boyutu için
              rolling tahmin testi yapıldı. Her W için α = 2/(W+1) alındı. Ölçüt: Ortalama Mutlak Hata (MAE).
            </p>
            <div className="overflow-x-auto mb-3">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-slate-300 text-left py-1.5 pr-3">W</th>
                    <th className="text-slate-300 text-left py-1.5 pr-3">α</th>
                    <th className="text-slate-300 text-left py-1.5 pr-3">MAE 2024</th>
                    <th className="text-slate-300 text-left py-1.5 pr-3">MAE 2025</th>
                    <th className="text-slate-300 text-left py-1.5 pr-3">Fark</th>
                    <th className="text-slate-300 text-left py-1.5">MAE tüm</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    [3,  '0.500', '13.39', '12.14', '1.25', '12.65'],
                    [4,  '0.400', '11.31', '12.39', '1.08', '11.48'],
                    [5,  '0.333', '10.97', '11.93', '0.96', '11.29'],
                    [6,  '0.286',  '9.05', '12.68', '3.63', '10.89'],
                    [7,  '0.250',  '9.65', '13.11', '3.46', '11.28'],
                    [8,  '0.222', '10.53', '14.85', '4.32', '11.75'],
                    [9,  '0.200', '10.77', '12.17', '1.40', '11.95'],
                    [10, '0.182', '15.65', '14.54', '1.11', '12.94'],
                    [11, '0.167', '24.52',  '5.18','19.34', '13.65'],
                  ].map(([w, a, m24, m25, fark, mall]) => {
                    const best = w === 5
                    const warn = Number(String(fark)) > 3
                    return (
                      <tr key={String(w)} className={`border-b border-slate-800 ${best ? 'bg-emerald-900/30' : warn ? 'bg-rose-950/30' : ''}`}>
                        <td className={`py-1.5 pr-3 font-bold ${best ? 'text-emerald-400' : 'text-white'}`}>{w}{best ? ' ◄' : ''}</td>
                        <td className="text-slate-300 py-1.5 pr-3">{a}</td>
                        <td className="text-white py-1.5 pr-3">{m24}</td>
                        <td className="text-white py-1.5 pr-3">{m25}</td>
                        <td className={`py-1.5 pr-3 font-bold ${warn ? 'text-rose-400' : 'text-emerald-400'}`}>{fark}</td>
                        <td className={`py-1.5 font-bold ${best ? 'text-emerald-400' : 'text-white'}`}>{mall}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="bg-emerald-950/40 border border-emerald-700/40 rounded-xl px-4 py-3 mb-2">
              <p className="text-emerald-300 text-xs font-semibold mb-1">Seçilen: W = 5 ay (α = 0.333)</p>
              <p className="text-white text-xs leading-relaxed">
                W=6 birleşik MAE'de en iyi görünüyor (10.89) ancak yıllar arası tutarsız:
                2024'te MAE=9.05 iken 2025'te 12.68'e çıkıyor (fark=3.63). W=5 her iki yılda da
                benzer hata veriyor (fark sadece 0.96) — daha güvenilir genellenebilirlik.
              </p>
            </div>
            <div className="bg-rose-950/30 border border-rose-700/30 rounded-xl px-4 py-2 mb-2">
              <p className="text-rose-300 text-xs leading-relaxed">
                W=6–8 arası kırmızı: 2025'te hata belirgin artıyor çünkü 2025 güçlü yukarı trend
                içeriyor (pct: 79→131), uzun pencere bu trendi yavaş takip ediyor.
                W=11: 2024'te 24.52, 2025'te 5.18 — yalnızca 1 test noktası olduğu için güvenilmez.
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl px-4 py-3">
              <p className="text-slate-200 text-xs font-semibold mb-2">MAE mi, MAPE mi?</p>
              <p className="text-white text-xs leading-relaxed mb-2">
                W=3–11 için her iki metrik de aynı pencere sıralamasını veriyor — W=5 her ikisinde de
                kazanıyor (MAE=11.29, MAPE=%11.09). Metrik seçimi bu veri setinde sonucu değiştirmiyor.
              </p>
              <p className="text-white text-xs leading-relaxed mb-2">
                <span className="text-emerald-300 font-semibold">MAE</span> → "ortalama X puan sapma" (hedef
                gerçekleşme oranı zaten % olduğu için MAE doğrudan anlamlı: ~11 puanlık tahmin hatası).
              </p>
              <p className="text-white text-xs leading-relaxed mb-2">
                <span className="text-emerald-300 font-semibold">MAPE</span> → birimsiz, farklı ölçeklerdeki
                bayilerle karşılaştırmada daha uygun. Gerçekleşme oranı sıfıra yaklaştığında
                (bölme problemi) yanıltıcı olabilir — bu veri setinde minimum %70, risk yok.
              </p>
              <p className="text-slate-300 text-xs leading-relaxed">
                <span className="text-amber-300 font-semibold">2025 Aralık özel notu:</span> Tüm pencereler
                Aralık'ı düşük tahmin etti (W=5: tahmin=105.9, gerçek=113.3, hata=−7.4). Önceki 3 ay
                zayıf gidişat gösteriyordu (107→88→113), model bu düşüşü taşıdı. W=8–9 Aralık'ta daha
                yakın çıktı (−4.2) ama tek aya göre pencere seçmek overfitting'dir — W=5 tercih edildi.
              </p>
            </div>
          </Accordion>
          <Accordion title="H skoru neden asimetrik?" icon={AlertCircle}>
            <p className="text-white text-sm leading-relaxed mb-2">
              Hedefini tutturan ya da geçen bayi cezalandırılmamalı — istediği kadar satsın.
              Sorun sadece geride kalanlarda. Dolayısıyla:
            </p>
            <code className="block bg-slate-900 rounded-lg px-4 py-3 text-emerald-400 font-mono text-xs mb-3 whitespace-pre-wrap">
{`beklenen_ytd = yıllık_hedef × (ay_no / 12)
gecikme      = max(0,  beklenen_ytd − gerçek_ytd)  / yıllık_hedef
H            = 1 + gecikme

Örnek (Haziran, ay=6):
  Yıllık hedef = 120, beklenen YTD = 60, gerçek YTD = 45
  gecikme = max(0, 60−45)/120 = 0.125
  H = 1.125  →  Temmuz'da ekstra araç alır

Hedefte ya da ileride:
  gerçek YTD = 65 ≥ 60  →  gecikme = max(0, −5)/120 = 0
  H = 1.0  →  ne penaltı ne ekstra`}
            </code>
          </Accordion>
          <Accordion title="±%20 kısıtı neden var?" icon={AlertCircle}>
            <p className="text-white text-sm leading-relaxed">
              Saf bir MCDM skoru bazen bir bayiye geçen yılın 3 katı araç verebilir; bu operasyonel
              olarak imkânsızdır (showroom kapasitesi, satış ekibi). ±%20 kısıtı, tahmin edilen aylık
              hedefe gore alt/üst sınır koyar.
            </p>
          </Accordion>
        </div>
      </section>

      {/* ── 6. Dağıtım Modülü ── */}
      <section>
        <SectionHeader icon={Truck} title="6. Dağıtım Modülü (MILP)" subtitle="Araçların bayilere optimal atanması" color="rose" />
        <div className="space-y-3">
          <Accordion title="Matematiksel model — MILP formülasyonu" icon={Code2} defaultOpen>
            <div className="space-y-3">
              <FormulSatir
                label="Karar değişkeni:"
                formula="x[v][d] ∈ {0, 1}  →  araç v, bayi d'ye atandı mı?"
                aciklama="Her araç tam olarak bir bayiye atanır (ya da atanmaz). Binary değişken; sürekli gevşetme yapılırsa LP, tamsayı gerekince MILP olur."
              />
              <FormulSatir
                label="Amaç fonksiyonu (minimize):"
                formula="∑_d  |allocated_d - target_d|  →  hedef sapmasını minimize et"
                aciklama="Mutlak değer, lineer programlamada iki pozitif değişkenle (over_d, under_d) linearize edilir. CBC solver bu formu doğrudan çözebilir."
              />
              <FormulSatir
                label="Kısıtlar:"
                formula={"∑_d x[v][d] ≤ 1  (her araç en fazla bir bayiye)\n∑_v x[v][d] ≤ kapasite_d"}
                aciklama="Stok kapasitesi kısıtı bu projede aktif değil (aylık 1000'den az araç). İlerde eklenebilir."
              />
            </div>
          </Accordion>
          <Accordion title="A Grubu / B Grubu ayrımı — neden?" icon={Layers}>
            <p className="text-white text-sm leading-relaxed mb-2">
              SUV segmentinde iki farklı platform bulunuyor:
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-blue-950/40 border border-blue-800/40 rounded-xl p-4">
                <p className="text-blue-300 font-bold text-sm mb-1">A Grubu</p>
                <p className="text-slate-200 text-xs">Kompakt SUV (A1V01, A2V02, A3V02 modelleri). Şehir içi, genç segment. Kent bayileri için daha uygun.</p>
              </div>
              <div className="bg-violet-950/40 border border-violet-800/40 rounded-xl p-4">
                <p className="text-violet-300 font-bold text-sm mb-1">B Grubu</p>
                <p className="text-slate-200 text-xs">Büyük SUV (B1V01 modeli). Aile / premium segment. Kırsal ve banliyö bayileri için daha uygun.</p>
              </div>
            </div>
            <p className="text-slate-200 text-xs mt-3 leading-relaxed">
              Gruplar bağımsız havuzlardan dağıtılır. Her bayiye A ve B hedefi ayrı girilir;
              allocate() fonksiyonu her grup için bağımsız çalıştırılır. Bu, A araçlarının yanlışlıkla
              B kotasından sayılmasını engeller.
            </p>
          </Accordion>
          <Accordion title="PuLP + CBC solver seçimi" icon={Cpu}>
            <p className="text-white text-sm leading-relaxed">
              <span className="text-emerald-400 font-semibold">PuLP</span>, Python için açık kaynak LP/MIP modelleme kütüphanesidir.
              Üretim ortamında Gurobi veya CPLEX daha hızlıdır; ancak akademik/demo bağlamında
              ücretsiz olan <span className="text-emerald-400 font-semibold">CBC (COIN-OR Branch and Cut)</span> solver yeterlidir.
              1.500 araç × 28 bayi problemini saniyeler içinde çözer.
              Cloud deployment için ek lisans gerekmez; GitHub Actions'ta da çalışır.
            </p>
          </Accordion>
          <Accordion title="Renk ve versiyon dağılımı — soft constraint" icon={Settings}>
            <p className="text-white text-sm leading-relaxed">
              Bayinin geçmiş satışlarından elde edilen renk vektörü (örn. %40 beyaz, %30 siyah, %20 gri)
              ile atanan araçların renk dağılımı arasındaki fark, amaç fonksiyonuna küçük bir ceza
              olarak eklenir. Bu sayede optimize edici tercihen bayinin sattığı renkleri öne çıkarır;
              ancak envanter kısıtı nedeniyle her zaman mümkün olmadığında görece kötü ama kabul
              edilebilir bir çözüm üretir.
            </p>
          </Accordion>
        </div>
      </section>

      {/* ── 7. Diğer Modüller ── */}
      <section>
        <SectionHeader icon={Globe} title="7. Diğer Modüller" subtitle="Geçmiş Analiz, Mevsimsellik, Bayi Harita" color="teal" />
        <div className="grid md:grid-cols-3 gap-4">
          <InfoCard title="Geçmiş Analiz" color="slate">
            <p className="text-slate-200 text-sm leading-relaxed">
              2024-2025 satış verisinin EDA (Exploratory Data Analysis) katmanı. Recharts ile
              bayi × model × renk bazında interaktif grafikler sunar. Sezonalite ve trend
              görselleştirme; outlier bayiler renkle vurgulanır.
            </p>
          </InfoCard>
          <InfoCard title="Mevsimsellik" color="slate">
            <p className="text-slate-200 text-sm leading-relaxed">
              STL çıktısının görsel sunumu. Bayilerin aylık seasonal_index değerleri ısı haritası
              ile gösterilir. Hangi ayda hangi bayinin satış hızlandığı, dağıtım zamanlamasını
              optimize etmek için kullanılır.
            </p>
          </InfoCard>
          <InfoCard title="Bayi Harita" color="slate">
            <p className="text-slate-200 text-sm leading-relaxed">
              Folium + Leaflet tabanlı interaktif harita. Bayiler pin ile gösterilir; renk,
              hedef gerçekleşme yüzdesini kodlar (yeşil ≥ %100, sarı %80-100, kırmızı &lt; %80).
              Coğrafi yoğunlaşma ve beyaz noktalar (bayi olmayan il) izlenebilir.
            </p>
          </InfoCard>
        </div>
      </section>

      {/* ── 8. Teknik Stack ── */}
      <section>
        <SectionHeader icon={Code2} title="8. Teknik Stack ve Mimari Kararlar" subtitle="Neden bu teknolojiler seçildi?" color="indigo" />
        <div className="space-y-3">
          <Accordion title="Frontend: React + TypeScript + Vite" icon={Globe} defaultOpen>
            <div className="grid md:grid-cols-3 gap-3">
              {[
                { tech: 'React 18', neden: 'Büyük ekosistem; component mimarisi, sayfa başına state yönetimi kolay; Recharts / Leaflet React entegrasyonları mevcut.' },
                { tech: 'TypeScript', neden: 'Tür güvenliği. Büyük veri yapıları (dealer hedefleri, envanter kayıtları) için compile-time hata yakalama kritik önem taşır.' },
                { tech: 'Vite', neden: 'CRA\'ya göre 10× daha hızlı HMR. Cloud ortamında build süresi kısadır. GitHub Actions build < 15 sn.' },
              ].map(({ tech, neden }) => (
                <div key={tech} className="bg-slate-900/60 rounded-xl p-4">
                  <p className="text-indigo-300 font-bold text-sm mb-1">{tech}</p>
                  <p className="text-slate-200 text-xs leading-relaxed">{neden}</p>
                </div>
              ))}
            </div>
          </Accordion>
          <Accordion title="Tailwind CSS — neden CSS framework?" icon={Layers}>
            <p className="text-white text-sm leading-relaxed">
              Utility-first yaklaşımı, prototiplemeyi hızlandırır; akademik projede tasarım zamanı
              kısıtlıdır. MUI/Ant Design gibi komponent kütüphaneleri daha ağır bundle üretir ve
              özelleştirmesi zordur. Tailwind, dark-mode ile tutarlı bir fintech estetiği sunar.
              Dashboard için koyu arka plan (slate-900) seçildi: veri yoğun sayfalarda göz yorulmaz,
              renk kontrastı yüksek olur.
            </p>
          </Accordion>
          <Accordion title="Recharts — neden bu grafik kütüphanesi?" icon={BarChart2}>
            <p className="text-white text-sm leading-relaxed">
              D3.js çok düşük seviyeli; her grafik için yüzlerce satır kod gerektirir.
              Chart.js React entegrasyonu daha az esnek. Recharts, React-native component API'si
              sunar; TypeScript desteği güçlüdür; SVG tabanlıdır (high-DPI ekranlarda net görünür).
              Animated çizgiler ve custom tooltip yazımı basittir.
            </p>
          </Accordion>
          <Accordion title="Python backend: pandas + PuLP + Prophet" icon={Cpu}>
            <div className="grid md:grid-cols-3 gap-3">
              {[
                { tech: 'pandas / numpy', neden: "Veri manipülasyonunun endüstri standardı. CSV'yi okuma, gruplama, pivot, merge işlemleri tek satırda." },
                { tech: 'PuLP + CBC', neden: 'Ücretsiz, cloud-uyumlu MILP solver. pip ile kurulur, lisans gerektirmez; 1500 araç < 1 dk.' },
                { tech: 'Prophet', neden: 'Tatil efektleri + deterministik mevsimsellik + logaritmik trend. Statsmodels ARIMA\'ya göre hiperparametre ayarı daha kolay.' },
              ].map(({ tech, neden }) => (
                <div key={tech} className="bg-slate-900/60 rounded-xl p-4">
                  <p className="text-sky-300 font-bold text-sm mb-1">{tech}</p>
                  <p className="text-slate-200 text-xs leading-relaxed">{neden}</p>
                </div>
              ))}
            </div>
          </Accordion>
          <Accordion title="Deployment: Tamamen bulut tabanlı" icon={Globe}>
            <div className="grid md:grid-cols-2 gap-3">
              {[
                { katman: 'GitHub Actions', aciklama: 'Her push\'ta ruff lint + pytest çalışır. main branch build zorunlu. Manual onay olmadan merge yapılamaz.' },
                { katman: 'Vercel (Frontend)', aciklama: 'main branch\'i izler, otomatik deploy eder. CDN üzerinde dağıtık; her commit preview URL alır.' },
                { katman: 'GitHub Codespaces', aciklama: 'Python analiz notebook\'ları için gerektiğinde açılır. Lokal kurulum gerektirmez.' },
                { katman: 'SQLite + pathlib', aciklama: 'Tüm path\'lar relative; cloud ortamında absolute path yok. Vercel Edge\'de DB gereksiz; statik JSON üretilip public/data altına konur.' },
              ].map(({ katman, aciklama }) => (
                <div key={katman} className="bg-slate-900/60 rounded-xl p-4">
                  <p className="text-teal-300 font-bold text-sm mb-1">{katman}</p>
                  <p className="text-slate-200 text-xs leading-relaxed">{aciklama}</p>
                </div>
              ))}
            </div>
          </Accordion>
        </div>
      </section>

      {/* ── 9. Sistem Akışı ── */}
      <section>
        <SectionHeader icon={GitBranch} title="9. Uçtan Uca Sistem Akışı" subtitle="Veri girişinden dağıtım kararına kadar adım adım" color="emerald" />
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
          <div className="space-y-3">
            {[
              { num: 1, title: 'Veri Yükleme', detail: 'Her ay sonunda geçmiş satış CSV\'si, aylık gerçekleşme ve yeni envanter dosyası sisteme yüklenir. Python pipeline CSV\'leri SQLite\'a aktarır.', color: 'blue' },
              { num: 2, title: 'SI Hesaplama (STL)', detail: 'Her bayinin 2024–2025 aylık satış serisi Trend × Mevsimsellik × Kalıntı olarak ayrıştırılır. Her bayi × ay kombinasyonu için Seasonal Index (SI) elde edilir. SI > 1 o ay güçlü, SI < 1 zayıf demektir.', color: 'violet' },
              { num: 3, title: 'Bayi Satış Profili', detail: 'Her bayinin 2024–2025 satışları model bazında ayrıştırılır: A1V01 / A2V02 / A3V02 / B1V01 oranları hesaplanır. Bu "profil vektörü" hem LP skorunda hem aylık model grubu dağılımında kullanılır.', color: 'sky' },
              { num: 4, title: 'Yıllık Pazar Payı', detail: '%50 bayinin 2025 satış payı + %50 TÜİK il bazlı araç stoku formülüyle her bayinin 10.000 araç içindeki yıllık hedef payı belirlenir. Yeni bayiler tamamen kapasite bazlı başlar.', color: 'amber' },
              { num: 5, title: 'Aylık Tahmin (Prophet)', detail: 'Hiyerarşik yapıda toplam pazar için 12 aylık projeksiyon üretilir, ardından bayi bazına indirgenir. Lansman yılı için ×1.11 boost uygulanır.', color: 'indigo' },
              { num: 6, title: 'LP Skoru (Cosine Similarity)', detail: 'Adım 3\'teki bayi profil vektörü ile o ayki envanter vektörü arasındaki cosine similarity hesaplanır. Bayinin sattığı modeller stoğa ne kadar benziyorsa LP skoru o kadar yüksek çıkar.', color: 'sky' },
              { num: 7, title: 'MCDM Aylık Kota', detail: 'Dört kriter ağırlıklı toplanır: P (geçmiş performans, %25) + LP (lokasyon-ürün uyumu, %35) + S (SI\'dan gelen mevsimsel uyum, %20) + H (yıllık hedefe yakınlık, %20). Skor orantılı aylık kota dağıtılır, ±%20 kısıtı uygulanır.', color: 'emerald' },
              { num: 8, title: 'Model Grubu Dağılımı', detail: 'Adım 7\'deki aylık kota, adım 3\'teki profil oranlarına göre A grubu ve B grubu olarak ikiye ayrılır. Örneğin Bayi 07\'nin kotası %55 A / %45 B ise hedefleri buna göre belirlenir.', color: 'amber' },
              { num: 9, title: 'MILP Araç Atama', detail: 'Envanter havuzu yüklenir. Her araç için x[araç][bayi] ∈ {0,1} karar değişkeni tanımlanır. A ve B grupları bağımsız çözülür. Hedef sapmasını minimize eden çözüm CBC solver ile bulunur.', color: 'rose' },
              { num: 10, title: 'Dashboard & Görselleştirme', detail: 'Dağıtım sonuçları, fill rate, boşluk analizi ve harita üzerinde sunulur. Kullanıcı hedefleri manuel değiştirebilir ve sistemi yeniden çalıştırabilir.', color: 'teal' },
            ].map(({ num, title, detail, color }) => {
              const dotColor: Record<string,string> = {
                blue:'bg-blue-500',violet:'bg-violet-500',sky:'bg-sky-500',
                amber:'bg-amber-500',emerald:'bg-emerald-500',rose:'bg-rose-500',
                teal:'bg-teal-500',indigo:'bg-indigo-500'
              }
              return (
                <div key={num} className="flex gap-4 items-start">
                  <div className="flex flex-col items-center flex-shrink-0">
                    <div className={`w-8 h-8 rounded-full ${dotColor[color]} flex items-center justify-center text-white text-xs font-bold`}>
                      {num}
                    </div>
                    {num < 7 && <div className="w-px h-6 bg-slate-700 mt-1" />}
                  </div>
                  <div className="pb-2">
                    <p className="text-white font-semibold text-sm">{title}</p>
                    <p className="text-slate-200 text-xs mt-0.5 leading-relaxed">{detail}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── 10. Kısıtlar ve Gelecek ── */}
      <section>
        <SectionHeader icon={Users} title="10. Kısıtlar, Varsayımlar ve Gelecek Çalışmalar" subtitle="Sistemin sınırları ve iyileştirme alanları" color="rose" />
        <div className="grid md:grid-cols-2 gap-4">
          <InfoCard title="Mevcut kısıtlar ve varsayımlar" color="rose">
            {[
              'Araç stoğu kapasitesi kısıtı YOK (≤ 1000 araç/ay sığar)',
              'Bayi teslimat süresi modele dahil değil (lojistik maliyeti)',
              'Müşteri bekleme süresi verisi yok (demand impatience)',
              'Envanter dosyası manuel yükleniyor; ERP entegrasyonu yok',
              'Renk / versiyon soft constraint katsayıları uzman görüşü gerektiriyor',
            ].map(k => (
              <div key={k} className="flex items-start gap-2 py-1.5 border-b border-slate-700/40 last:border-0">
                <AlertCircle size={13} className="text-rose-400 mt-0.5 flex-shrink-0" />
                <p className="text-white text-xs leading-relaxed">{k}</p>
              </div>
            ))}
          </InfoCard>
          <InfoCard title="Gelecek çalışma önerileri" color="emerald">
            {[
              'ERP/DMS API entegrasyonu ile real-time veri akışı',
              'Müşteri tercih verisi ile demand forecasting iyileştirmesi',
              'Lojistik maliyet kısıtının MILP modeline eklenmesi',
              'Reinforcement Learning ile dinamik allokasyon (çok dönemli)',
              'Bayilere anında anlık güncelleme için WebSocket push notifikasyon',
              'A/B test: sistem kararı vs. manuel karar performans karşılaştırması',
            ].map(k => (
              <div key={k} className="flex items-start gap-2 py-1.5 border-b border-slate-700/40 last:border-0">
                <CheckCircle size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                <p className="text-white text-xs leading-relaxed">{k}</p>
              </div>
            ))}
          </InfoCard>
        </div>
      </section>

      {/* ── Footer ── */}
      <div className="text-center py-6 border-t border-slate-800">
        <p className="text-slate-200 text-xs">
          Endüstri Mühendisliği Bitirme Projesi · 2026 · Demo Modu
        </p>
        <p className="text-slate-500 text-xs mt-1">
          Vehicle Allocation Problem · MCDM · MILP · STL + Prophet · Collaborative Filtering
        </p>
      </div>
    </div>
  )
}
