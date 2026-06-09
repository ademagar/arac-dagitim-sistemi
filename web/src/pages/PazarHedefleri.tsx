import { useEffect, useState } from 'react'

// ---------------------------------------------------------------------------
// Tipler
// ---------------------------------------------------------------------------

interface PazarKapasiteSatiri {
  dealer: string
  il: string
  ilce: string
  il_kendi_pay: number
  komsular: { il: string; pay: number }[]
  catchment_pay: number
  n_il: number
  capacity_per_dealer: number
  brand_pay_2025: number
  target_pay_2026: number
  yeni_bayi: boolean
  hedef_8500: number
  hedef_10000: number
}

interface PazarKapasitesi {
  tablo: PazarKapasiteSatiri[]
}

interface TahminData {
  pazar_kapasitesi?: PazarKapasitesi
}

// ---------------------------------------------------------------------------
// Yardımcı bileşenler
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Formül Görselleştirme
// ---------------------------------------------------------------------------

function FormulKutusu() {
  return (
    <div className="bg-slate-900 rounded-2xl border border-slate-700 p-6">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-5">
        Hibrit Hedef Dağıtım Formülü
      </p>

      {/* Ana formül */}
      <div className="text-center mb-6">
        <div className="inline-block bg-slate-800 rounded-xl px-6 py-5 border border-slate-600 w-full max-w-2xl">
          <p className="text-sm md:text-base font-mono text-white leading-relaxed">
            <span className="text-blue-400 font-bold">target_pay</span>
            <span className="text-slate-400"> = </span>
            <span className="text-emerald-400 font-bold">0.5</span>
            <span className="text-slate-400"> × </span>
            <span className="text-amber-400">brand_pay_2025</span>
            <span className="text-slate-400"> + </span>
            <span className="text-emerald-400 font-bold">0.5</span>
            <span className="text-slate-400"> × </span>
            <span className="text-rose-400">(catchment_pay / n_bayis_in_il)</span>
          </p>
          <p className="text-xs text-slate-500 mt-2">
            → normalize: Σ target_pay = 100%
          </p>
        </div>
      </div>

      {/* Bileşen açıklamaları */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-amber-900/30 rounded-xl border border-amber-800/40 p-4">
          <p className="text-amber-300 font-semibold text-xs mb-2 uppercase tracking-wide">
            brand_pay_2025 — %50
          </p>
          <p className="text-amber-200/75 text-xs leading-relaxed">
            Bayinin 2025 yılında markalı araç satışlarındaki payı.
            Geçmiş performansı ödüllendirir. Yeni bayilerde (Dealer 23–28) = 0,
            tamamen pazar kapasitesine göre başlarlar.
          </p>
        </div>
        <div className="bg-rose-900/30 rounded-xl border border-rose-800/40 p-4">
          <p className="text-rose-300 font-semibold text-xs mb-2 uppercase tracking-wide">
            catchment_pay — %50 (payda)
          </p>
          <p className="text-rose-200/75 text-xs leading-relaxed">
            İlin hizmet alanı pazar payı: il'in kendi TÜİK araç stok payı +
            komşu illerin ağırlıklı katkısı. Gerçek müşteri çekim alanını temsil eder.
          </p>
        </div>
        <div className="bg-indigo-900/30 rounded-xl border border-indigo-800/40 p-4">
          <p className="text-indigo-300 font-semibold text-xs mb-2 uppercase tracking-wide">
            n_bayis_in_il — bölücü
          </p>
          <p className="text-indigo-200/75 text-xs leading-relaxed">
            Aynı ildeki bayi sayısı. İstanbul'da 7, Ankara'da 2, İzmir'de 2,
            Bursa'da 2, Tekirdağ'da 2 bayi. Catchment payı eşit paylaştırılır.
          </p>
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-4 text-center">
        Kaynak: TÜİK Motorlu Kara Taşıtları İstatistikleri, Aralık 2024 (Bülten No: 53463) · 31.301.389 kayıtlı araç
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Neden Pazar Kapasitesi? — Uzun Anlatı
// ---------------------------------------------------------------------------

function NarrativeSection() {
  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl border border-slate-700 p-8 text-white">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-3">
          Metodoloji — Neden Pazar Kapasitesi Bazlı Dağıtım?
        </p>
        <h2 className="text-2xl font-bold text-white mb-6 leading-snug">
          Tarihsel veri tek başına yeterli değildir.
        </h2>

        <div className="space-y-5 text-sm text-slate-300 leading-relaxed">
          <p>
            Geleneksel araç dağıtım sistemlerinde bayilere bir önceki dönemin satış
            performansı baz alınarak hedef verilir. Bu yaklaşım ilk bakışta mantıklı
            görünse de zamanla bir kısır döngü oluşturur:{' '}
            <strong className="text-white">
              yüksek potansiyelli ama az desteklenen bayiler kısıtlı stokla çalışmaya
              mahkum kalırken, köklü bayiler avantajlı konumlarını korur.
            </strong>
          </p>

          <p>
            Daha da kritik bir sorun,{' '}
            <strong className="text-white">
              yeni bayilerin bu sistemde hiçbir geçmiş performans verisi olmadığı için
              sıfırdan başlamasıdır.
            </strong>{' '}
            2026 yılında ağımıza katılan 6 yeni bayi (Dealer 23–28), geçmiş satış
            verisine dayanılarak oluşturulan dağıtım modelinde görünmez kalır. Oysa
            bu bayilerin bulundukları pazarlar — Bursa, Samsun, İstanbul, Tekirdağ
            ve Sivas — kendi başlarına önemli potansiyel taşımaktadır.
          </p>

          <p>
            Bu sorunun çözümü için{' '}
            <strong className="text-white">iki boyutlu bir yaklaşım</strong> geliştirildi.
            Geçmiş performansın yarısını koruyan, geri kalan yarısını ise{' '}
            <em>nesnel pazar büyüklüğüne</em> bağlayan bir hibrit formül uygulandı.
            Pazar büyüklüğü ölçümünde TÜİK'in Aralık 2024 araç stok verisi kullanıldı:
            Türkiye genelinde kayıtlı{' '}
            <strong className="text-white">31,3 milyon araç</strong>, il bazında
            hesaplanan paylarla kıyaslandı.
          </p>

          <p>
            <strong className="text-white">Yakalama Alanı (Catchment Area)</strong>{' '}
            kavramı, gerçek dünya bayi davranışını modele dahil eder. Bir bayi yalnızca
            kendi ilini değil, komşu illerdeki müşterileri de çekebilir. Örneğin
            İstanbul bayileri Tekirdağ ve Kırklareli pazarından; Ankara bayileri
            Eskişehir ve Çankırı'dan faydalanabilir. Her ilin catchment alanı, il
            kendi payına komşu illerin ağırlıklı katkısı eklenerek hesaplandı.
          </p>

          <p>
            <strong className="text-white">Aynı ilde birden fazla bayi</strong>{' '}
            olduğunda (İstanbul'da 7, Ankara'da 2, İzmir'de 2, Bursa'da 2,
            Tekirdağ'da 2), ilin catchment payı eşit bölüştürülür. Bu, rekabetin
            zaten yüksek olduğu büyük pazarlarda aşırı tahsisin önüne geçer ve
            bayiler arasındaki dengeyi korur.
          </p>

          <p>
            Son olarak, formülden çıkan ham paylar normalize edilir: 28 bayinin
            paylarının toplamı her zaman{' '}
            <strong className="text-white">%100</strong> olacak şekilde ölçeklenir.
            Bu normalizasyon, pazar payı verilerindeki küçük ölçüm farklılıklarına
            rağmen sistemin tutarlı ve dağıtım toplamını koruyan sonuçlar üretmesini sağlar.
          </p>
        </div>

        {/* Kavramsal çerçeve */}
        <div className="mt-7 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="bg-white/5 rounded-xl border border-white/10 p-3">
            <p className="text-xs font-semibold text-blue-300 mb-1">Akademik Çerçeve</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Vehicle Allocation Problem (VAP) · Multi-Criteria Decision Making (MCDM) ·
              Assortment Optimization. Geçmiş + kapasite hibrit yaklaşım literatürde
              "demand-weighted allocation" olarak sınıflandırılır.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl border border-white/10 p-3">
            <p className="text-xs font-semibold text-emerald-300 mb-1">Pratik Avantaj</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Kısır döngüyü kırar · Yeni bayilere adil başlangıç · Pazar dinamiklerine
              duyarlı · Her yıl otomatik güncellenir (satış + TÜİK verileriyle).
            </p>
          </div>
          <div className="bg-white/5 rounded-xl border border-white/10 p-3">
            <p className="text-xs font-semibold text-amber-300 mb-1">Veri Kaynakları</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              TÜİK Bülten 53463 (Ara 2024) · ODMD Ocak 2025 Basın Bülteni ·
              SUV pazar payı %56,8 · Türkiye toplam araç stoğu 31,3M.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ana Sayfa
// ---------------------------------------------------------------------------

export default function PazarHedefleri() {
  const [data, setData] = useState<TahminData | null>(null)
  const [senaryo, setSenaryo] = useState<8500 | 10000>(8500)
  const [siralama, setSiralama] = useState<'dealer' | 'hedef' | 'catchment'>('hedef')
  const [siralamaYon, setSiralamaYon] = useState<'desc' | 'asc'>('desc')

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

  const pk = data.pazar_kapasitesi
  if (!pk) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-8 text-center">
        <p className="text-amber-700 font-medium text-lg mb-2">Pazar kapasitesi verisi bulunamadı.</p>
        <p className="text-amber-600 text-sm">scripts/gen_tahmin.py çalıştırılarak tahmin.json güncellenmelidir.</p>
      </div>
    )
  }

  const tablo = pk.tablo
  const iller = [...new Set(tablo.map(r => r.il))]

  function toggleSort(alan: typeof siralama) {
    if (siralama === alan) setSiralamaYon(d => d === 'asc' ? 'desc' : 'asc')
    else { setSiralama(alan); setSiralamaYon('desc') }
  }

  const sirali = [...tablo].sort((a, b) => {
    let av: number | string, bv: number | string
    if (siralama === 'dealer') { av = a.dealer; bv = b.dealer }
    else if (siralama === 'hedef') {
      av = senaryo === 8500 ? a.hedef_8500 : a.hedef_10000
      bv = senaryo === 8500 ? b.hedef_8500 : b.hedef_10000
    } else {
      av = a.catchment_pay; bv = b.catchment_pay
    }
    if (typeof av === 'string') return siralamaYon === 'asc'
      ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return siralamaYon === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const thKlasi = 'text-right py-3 px-3 font-semibold min-w-[80px] cursor-pointer select-none hover:brightness-125 transition-all'
  const sortIkon = (alan: typeof siralama) =>
    siralama === alan ? (siralamaYon === 'desc' ? ' ↓' : ' ↑') : ''

  const toplam8500  = tablo.reduce((s, r) => s + r.hedef_8500,  0)
  const toplam10000 = tablo.reduce((s, r) => s + r.hedef_10000, 0)
  const yeniBayi    = tablo.filter(r => r.yeni_bayi).length

  return (
    <div className="max-w-7xl mx-auto space-y-8">

      {/* Sayfa başlığı */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Pazar Bazlı Bayi Hedefleri</h1>
        <p className="text-slate-500 text-sm mt-1">
          Hibrit dağıtım formülü · TÜİK araç stok verisi bazlı catchment · 28 bayi · 2026 yıllık hedefler
        </p>
      </div>

      {/* Özet metrikler */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Toplam Bayi"
          value="28"
          sub={`${yeniBayi} yeni · ${28 - yeniBayi} mevcut`}
          colorClass="bg-white border-slate-200"
        />
        <MetricCard
          label="Kapsanan İl"
          value={String(iller.length)}
          sub="farklı il, 18 catchment alanı"
          colorClass="bg-blue-50 border-blue-200"
        />
        <MetricCard
          label="8.500 Senaryo"
          value={toplam8500.toLocaleString('tr')}
          sub="araç — muhafazakâr büyüme"
          colorClass="bg-slate-50 border-slate-200"
        />
        <MetricCard
          label="10.000 Senaryo"
          value={toplam10000.toLocaleString('tr')}
          sub="araç — agresif büyüme"
          colorClass="bg-emerald-50 border-emerald-200"
        />
      </div>

      {/* Anlati */}
      <NarrativeSection />

      {/* Formül */}
      <FormulKutusu />

      {/* Veri kaynakları */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
          <p className="text-xs font-semibold text-blue-800 mb-1">TÜİK — Araç Stok Verisi</p>
          <p className="text-xs text-blue-700 mb-2">
            Motorlu Kara Taşıtları İstatistikleri, Aralık 2024.
            Toplam 31.301.389 kayıtlı araç. İl bazında catchment payı hesabında kullanıldı.
          </p>
          <p className="text-xs text-blue-500 font-mono">Bülten No: 53463</p>
        </div>
        <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4">
          <p className="text-xs font-semibold text-emerald-800 mb-1">ODMD — Segment Verisi</p>
          <p className="text-xs text-emerald-700 mb-2">
            2024 yılı toplam 980.341 araç satışı. SUV segmenti: %56,8 (556.548 adet).
            B+C (mainstream): %85,2. D+E+F (premium): %14,3.
          </p>
          <p className="text-xs text-emerald-500 font-mono">ODMD Ocak 2025 Basın Bülteni</p>
        </div>
        <div className="bg-amber-50 rounded-xl border border-amber-200 p-4">
          <p className="text-xs font-semibold text-amber-800 mb-1">Pazar Yoğunlaşması</p>
          <p className="text-xs text-amber-700 mb-2">
            İstanbul: yeni araç kayıtlarının %25,1'i (651.282 / 2.598.816).
            Ankara: %7,0 (181.655). Proxy doğrulama: TÜİK / Emniyet Trafik 2024.
          </p>
          <p className="text-xs text-amber-500 font-mono">TÜİK · Emniyet Genel Müdürlüğü</p>
        </div>
      </div>

      {/* === 28 BAYİ DETAY TABLOSU === */}
      <div>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Bayi Bazlı Pazar Hedef Tablosu
            </h2>
            <span className="text-xs bg-emerald-100 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full font-medium">
              {yeniBayi} yeni bayi
            </span>
          </div>

          {/* Senaryo seçici */}
          <div className="flex gap-2">
            {([8500, 10000] as const).map(h => (
              <button
                key={h}
                onClick={() => setSenaryo(h)}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all ${
                  senaryo === h
                    ? 'border-blue-500 bg-blue-50 text-blue-800'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                }`}
              >
                {h.toLocaleString('tr')} araç
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-slate-800 text-white">
                <th
                  className="text-left py-3 px-3 font-semibold sticky left-0 bg-slate-800 z-10 min-w-[120px] cursor-pointer select-none hover:brightness-125"
                  onClick={() => toggleSort('dealer')}
                >
                  Bayi{sortIkon('dealer')}
                </th>
                <th className="text-left py-3 px-3 font-semibold min-w-[140px]">
                  İl / İlçe
                </th>
                <th
                  className={`${thKlasi} bg-blue-900`}
                  onClick={() => toggleSort('catchment')}
                  title="İlin TÜİK araç payı + komşu il katkıları"
                >
                  Catchment %{sortIkon('catchment')}
                </th>
                <th className="text-right py-3 px-3 font-semibold min-w-[55px]">
                  n İl
                </th>
                <th className="text-right py-3 px-3 font-semibold min-w-[90px] bg-indigo-900"
                  title="catchment_pay / n_bayis_in_il">
                  Cap/Bayi %
                </th>
                <th className="text-right py-3 px-3 font-semibold min-w-[85px] bg-amber-900">
                  2025 Marka %
                </th>
                <th className="text-right py-3 px-3 font-semibold min-w-[85px] bg-emerald-900 border-r border-slate-600">
                  2026 Hedef %
                </th>
                <th
                  className={`${thKlasi} bg-slate-700`}
                  onClick={() => toggleSort('hedef')}
                >
                  {senaryo.toLocaleString('tr')} araç{sortIkon('hedef')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sirali.map((row, idx) => (
                <tr
                  key={row.dealer}
                  className={`border-b border-slate-100 transition-colors ${
                    row.yeni_bayi
                      ? 'bg-emerald-50/60 hover:bg-emerald-50'
                      : idx % 2 === 0
                      ? 'bg-white hover:bg-blue-50/30'
                      : 'bg-slate-50/30 hover:bg-blue-50/30'
                  }`}
                >
                  <td className="py-2.5 px-3 sticky left-0 z-10 font-semibold text-slate-700 bg-inherit">
                    <div className="flex items-center gap-1.5">
                      {row.dealer}
                      {row.yeni_bayi && (
                        <span className="text-xs bg-emerald-600 text-white px-1.5 py-0.5 rounded font-medium">
                          YENİ
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    <span className="font-semibold text-slate-700">{row.il}</span>
                    <span className="text-slate-400"> / {row.ilce}</span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-blue-700 font-semibold">
                    {row.catchment_pay.toFixed(2)}%
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-slate-500">
                    {row.n_il}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-indigo-700">
                    {row.capacity_per_dealer.toFixed(3)}%
                  </td>
                  <td className={`py-2.5 px-3 text-right font-mono ${
                    row.yeni_bayi ? 'text-slate-400 italic' : 'text-amber-700 font-semibold'
                  }`}>
                    {row.yeni_bayi ? '—' : `${row.brand_pay_2025.toFixed(3)}%`}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-emerald-700 font-bold border-r border-slate-200">
                    {row.target_pay_2026.toFixed(3)}%
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-800">
                    <span className={senaryo === 8500 ? '' : 'text-blue-700'}>
                      {(senaryo === 8500 ? row.hedef_8500 : row.hedef_10000).toLocaleString('tr')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-slate-100 border-t-2 border-slate-300 font-bold">
                <td className="py-3 px-3 text-slate-800 sticky left-0 bg-slate-100 z-10" colSpan={2}>
                  TOPLAM
                </td>
                <td className="py-3 px-3 text-right font-mono text-slate-400 text-xs">—</td>
                <td />
                <td className="py-3 px-3 text-right font-mono text-slate-400 text-xs">—</td>
                <td className="py-3 px-3 text-right font-mono text-amber-700">
                  {tablo.filter(r => !r.yeni_bayi).reduce((s, r) => s + r.brand_pay_2025, 0).toFixed(2)}%
                  <span className="block text-xs font-normal text-slate-400">mevcut bayiler</span>
                </td>
                <td className="py-3 px-3 text-right font-mono text-emerald-700 border-r border-slate-300">
                  {tablo.reduce((s, r) => s + r.target_pay_2026, 0).toFixed(2)}%
                </td>
                <td className="py-3 px-3 text-right font-mono text-slate-800">
                  {(senaryo === 8500
                    ? tablo.reduce((s, r) => s + r.hedef_8500,  0)
                    : tablo.reduce((s, r) => s + r.hedef_10000, 0)
                  ).toLocaleString('tr')}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-1.5 mt-3 text-xs text-slate-500">
          <span>
            <span className="inline-block w-3 h-3 rounded bg-emerald-100 border border-emerald-300 mr-1 align-middle" />
            YENİ = 2026'da ağa katılan (geçmiş satış verisi yok, brand_pay_2025 = 0)
          </span>
          <span>Catchment = İl payı + komşu iller (TÜİK araç stoğu bazlı)</span>
          <span>n İl = Aynı ilde toplam bayi sayısı</span>
          <span>Sütun başlıklarına tıklayarak sıralayabilirsiniz</span>
        </div>
      </div>

      {/* === İL BAZLI KAPASİTE KARTLARI === */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
          İl Bazlı Pazar Kapasitesi — Bayi Dağılımı
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {iller
            .sort((a, b) => {
              const aPay = tablo.find(r => r.il === a)?.catchment_pay ?? 0
              const bPay = tablo.find(r => r.il === b)?.catchment_pay ?? 0
              return bPay - aPay
            })
            .map(il => {
              const ilDealers = tablo.filter(r => r.il === il)
              const firstRow = ilDealers[0]
              if (!firstRow) return null
              const toplamHedef = ilDealers.reduce(
                (s, d) => s + (senaryo === 8500 ? d.hedef_8500 : d.hedef_10000), 0
              )
              return (
                <div
                  key={il}
                  className="bg-white rounded-xl border border-slate-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-sm font-bold text-slate-800">{il}</p>
                      <p className="text-xs text-slate-400">
                        {ilDealers.length} bayi ·{' '}
                        <span className="text-blue-600">%{firstRow.catchment_pay.toFixed(2)} catchment</span>
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-400">{senaryo.toLocaleString('tr')}'de</p>
                      <p className="text-sm font-bold text-slate-700">{toplamHedef.toLocaleString('tr')} araç</p>
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    {ilDealers.map(d => (
                      <div key={d.dealer} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-600">{d.dealer}</span>
                          {d.yeni_bayi && (
                            <span className="text-emerald-600 font-semibold text-xs">YENİ</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2.5">
                          <span className="text-slate-500 font-mono">
                            {(senaryo === 8500 ? d.hedef_8500 : d.hedef_10000).toLocaleString('tr')}
                          </span>
                          <span className="font-mono font-semibold text-emerald-700 w-12 text-right">
                            %{d.target_pay_2026.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-2.5 pt-2 border-t border-slate-100 text-xs text-slate-400 flex justify-between">
                    <span>Cap/bayi: %{firstRow.capacity_per_dealer.toFixed(3)}</span>
                    <span className="text-slate-300">|</span>
                    <span>İl kendi: %{firstRow.il_kendi_pay.toFixed(2)}</span>
                  </div>
                </div>
              )
            })}
        </div>
      </div>

    </div>
  )
}
