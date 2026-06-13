import { useEffect, useState } from 'react'

// ---------------------------------------------------------------------------
// Tipler
// ---------------------------------------------------------------------------

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

interface AralikOzet {
  toplam_tahmin: number
  toplam_gercek: number
  mape: number
  yontem: string
}

interface BayiAylikModelHedef {
  ay: number
  ay_adi: string
  toplam: number
  modeller: Record<string, number>
}

interface BayiHedef {
  tier: 'A' | 'B' | 'C'
  il?: string
  ilce?: string
  brand_pay_2025?: number
  target_pay_2026?: number
  yeni_bayi?: boolean
  aylik: BayiAylikModelHedef[]
  yillik_toplam: number
  yillik_modeller: Record<string, number>
  yillik_segmentler: Record<string, number>
}

interface TahminData {
  aralik_tahmin: {
    ozet: AralikOzet
    tier_ozet: TierOzet[]
  }
  bayi_aylik_hedefler: {
    senaryo_8500: Record<string, BayiHedef>
    senaryo_10000: Record<string, BayiHedef>
  }
}

// ---------------------------------------------------------------------------
// Yardımcı
// ---------------------------------------------------------------------------

function Karti({ baslik, deger, alt, renk }: {
  baslik: string; deger: string; alt?: string; renk?: string
}) {
  return (
    <div className={`rounded-xl border p-4 ${renk ?? 'bg-white border-slate-200'}`}>
      <p className="text-xs font-medium text-slate-500 mb-1">{baslik}</p>
      <p className="text-2xl font-bold text-slate-900">{deger}</p>
      {alt && <p className="text-xs text-slate-400 mt-0.5">{alt}</p>}
    </div>
  )
}

function Bolum({ no, baslik, alt, children }: {
  no: string; baslik: string; alt: string; children: React.ReactNode
}) {
  return (
    <section className="space-y-5">
      <div className="flex items-start gap-4">
        <span className="flex-shrink-0 w-9 h-9 rounded-full bg-blue-600 text-white text-sm font-bold flex items-center justify-center">
          {no}
        </span>
        <div>
          <h2 className="text-lg font-bold text-slate-900">{baslik}</h2>
          <p className="text-sm text-slate-500">{alt}</p>
        </div>
      </div>
      {children}
    </section>
  )
}

const TIER_STYLE = {
  A: { bg: 'bg-blue-600',   light: 'bg-blue-50 border-blue-200',   text: 'text-blue-700',   badge: 'bg-blue-600 text-white' },
  B: { bg: 'bg-amber-500',  light: 'bg-amber-50 border-amber-200', text: 'text-amber-700',  badge: 'bg-amber-500 text-white' },
  C: { bg: 'bg-emerald-600',light: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', badge: 'bg-emerald-600 text-white' },
}

const TIER_ILLER = {
  A: ['İSTANBUL', 'ANKARA', 'İZMİR', 'BURSA'],
  B: ['ANTALYA', 'KOCAELİ', 'GAZİANTEP', 'TEKİRDAĞ', 'KONYA', 'MUĞLA', 'DENİZLİ'],
  C: ['ADANA', 'MERSİN', 'KAYSERİ', 'KAHRAMANMARAŞ', 'SAMSUN', 'TRABZON', 'SİVAS'],
}

const TIER_ACIKLAMA = {
  A: 'Büyük Metro',
  B: 'Bölgesel Merkez',
  C: 'Gelişen Pazar',
}

const MODEL_RENK: Record<string, string> = {
  A1V01: 'bg-violet-100 text-violet-800',
  A2V02: 'bg-blue-100 text-blue-800',
  A3V02: 'bg-sky-100 text-sky-800',
  B1V01: 'bg-amber-100 text-amber-800',
  B2V01: 'bg-orange-100 text-orange-800',
}

// ---------------------------------------------------------------------------
// Ana sayfa
// ---------------------------------------------------------------------------

export default function AylikBayiHedef() {
  const [data, setData] = useState<TahminData | null>(null)
  const [secili, setSecili] = useState('')

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    fetch(`${base}data/tahmin.json`)
      .then(r => r.json())
      .then((d: TahminData) => {
        setData(d)
        const bayiler = Object.keys(d.bayi_aylik_hedefler.senaryo_10000).sort(
          (a, b) => parseInt(a.split(' ')[1]) - parseInt(b.split(' ')[1])
        )
        setSecili(bayiler[0] ?? '')
      })
      .catch(err => console.error('tahmin.json yüklenemedi:', err))
  }, [])

  if (!data) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Yükleniyor…</div>
  }

  const { aralik_tahmin, bayi_aylik_hedefler } = data
  const senaryoData = bayi_aylik_hedefler.senaryo_10000
  const bayiler = Object.keys(senaryoData).sort((a, b) => parseInt(a.split(' ')[1]) - parseInt(b.split(' ')[1]))
  const bayiHedef = senaryoData[secili]
  const BILINEN = ['A1V01', 'A2V02', 'A3V02', 'B1V01']

  return (
    <div className="max-w-6xl mx-auto space-y-14">

      {/* Başlık */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Metodoloji & Aylık Bayi Hedefleri</h1>
        <p className="text-slate-500 text-sm mt-1">
          Projenin çözüm mantığı · A/B/C pazar gruplandırması · Mevsimsel ayrıştırma ·
          Aylık bayi × model hedeflerinin türetilmesi
        </p>
      </div>

      {/* ─────────────────────────────────────────────────────── */}
      {/* BÖLÜM 1 — PROJENİN MANTIĞI */}
      {/* ─────────────────────────────────────────────────────── */}
      <Bolum no="1" baslik="Projenin Mantığı: Ne Çözüyoruz?" alt="Kavramsal çerçeve — yöntem ve gerekçe">

        {/* Problem */}
        <div className="bg-slate-900 rounded-2xl p-7 text-white">
          <p className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-3">Problem</p>
          <h3 className="text-xl font-bold mb-5">
            Bir distribütör, her ay 28 bayiye 300–1.500 araç dağıtmak zorunda.
            <br />
            <span className="text-slate-400 text-base font-normal">
              Hangi bayiye kaç tane, hangi model, hangi ay?
            </span>
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed mb-4">
            Bu soru literatürde <strong className="text-white">Vehicle Allocation Problem (VAP)</strong> olarak
            tanımlanır. Teoride basit görünür: toplam arzı dağıt. Pratikte üç kısıt aynı anda
            geçerlidir:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              ['Talep Belirsizliği', 'Gelecek ay kaç araç satılacağı bilinmez. Yanlış tahmin → stok fazlası veya fırsatın kaçırılması.'],
              ['Bayi Heterojenliği', 'İstanbul\'daki bayi ile Sivas\'taki bayinin pazar büyüklüğü, müşteri profili ve model tercihi farklıdır.'],
              ['Stok & Model Kısıtı', 'Her model sınırlı. Distribütörün tüm 12 ay için model bazlı üretim planı yapması gerekir.'],
            ].map(([b, a]) => (
              <div key={b} className="bg-white/8 rounded-xl p-4 border border-white/10">
                <p className="text-xs font-semibold text-amber-300 mb-1">{b}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Çözüm yaklaşımı */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              no: '1',
              baslik: 'TAHMİN KATMANI',
              aciklama: 'Toplam pazar ne kadar satacak?',
              yontem: 'Mevsimsel Ayrıştırma (Multiplicative Decomposition)',
              detay: 'Satış serisi Trend × Mevsimsellik × Kalıntı olarak ayrıştırılır. Her tier grubu için ayrı Seasonal Index (SI) ve trend çarpanı hesaplanır. Bu, piyasanın doğal ritmini (Ocak düşük, Aralık yüksek) tahmine yansıtır.',
              renk: 'border-blue-200 bg-blue-50',
              renkText: 'text-blue-700',
            },
            {
              no: '2',
              baslik: 'DAĞITIM KATMANI',
              aciklama: 'Her bayi toplamın kaçta kaçını almalı?',
              yontem: 'Hibrit Pazar Payı Formülü (MCDM)',
              detay: 'Çok Kriterli Karar Verme (Multi-Criteria Decision Making) çerçevesinde iki kriter: %50 geçmiş marka performansı (2025 satış payı) + %50 pazar kapasitesi (TÜİK il bazlı araç stoku). Yeni bayiler için saf kapasite bazlı start.',
              renk: 'border-amber-200 bg-amber-50',
              renkText: 'text-amber-700',
            },
            {
              no: '3',
              baslik: 'AYRIŞTIRMA KATMANI',
              aciklama: 'Yıllık hedefi aya ve modele nasıl böleriz?',
              yontem: 'Hiyerarşik Top-Down Tahmin',
              detay: 'Yıllık bayi hedefi → SI çarpanlarıyla 12 aya → Bayinin tarihsel model karışımıyla (collaborative filtering) modellere dağıtılır. Aynı toplamı koruyan ve tutarlı bir hiyerarşi oluşturur.',
              renk: 'border-emerald-200 bg-emerald-50',
              renkText: 'text-emerald-700',
            },
          ].map(k => (
            <div key={k.no} className={`rounded-xl border p-5 ${k.renk}`}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`w-6 h-6 rounded-full ${k.renkText.replace('text-', 'bg-').replace('700','600')} text-white text-xs font-bold flex items-center justify-center`}>
                  {k.no}
                </span>
                <p className={`text-xs font-bold uppercase tracking-wide ${k.renkText}`}>{k.baslik}</p>
              </div>
              <p className={`text-sm font-semibold mb-2 ${k.renkText}`}>{k.aciklama}</p>
              <p className={`text-xs font-medium mb-2 ${k.renkText} opacity-80`}>Yöntem: {k.yontem}</p>
              <p className="text-xs text-slate-600 leading-relaxed">{k.detay}</p>
            </div>
          ))}
        </div>

        {/* Teknoloji */}
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Teknoloji Yığını</p>
          <div className="flex flex-wrap gap-3 text-xs">
            {[
              ['Python 3.11 + pandas', 'Veri manipülasyonu, pivot tablolar, group-by hesaplamalar'],
              ['numpy', 'Sayısal hesaplamalar, matris operasyonları, normalizasyon'],
              ['statsmodels (STL)', 'Seasonal-Trend Decomposition — mevsimsel indeks üretimi'],
              ['scikit-learn', 'Cosine similarity — collaborative filtering bazlı model mix hesabı'],
              ['PuLP + CBC Solver', 'Mixed Integer Linear Programming — gelecek dönem MILP optimizasyon'],
              ['Recharts + React', 'İnteraktif dashboard görselleştirme'],
            ].map(([isim, acik]) => (
              <div key={isim} className="bg-white rounded-lg border border-slate-200 px-3 py-2 max-w-[280px]">
                <p className="font-mono font-semibold text-slate-700">{isim}</p>
                <p className="text-slate-400 mt-0.5">{acik}</p>
              </div>
            ))}
          </div>
        </div>
      </Bolum>

      {/* ─────────────────────────────────────────────────────── */}
      {/* BÖLÜM 2 — A/B/C TIER GRUPLAMASI */}
      {/* ─────────────────────────────────────────────────────── */}
      <Bolum no="2" baslik="Pazar Büyüklüğüne Göre A/B/C Tier Gruplandırması" alt="Neden gruplandırma? Kriterler ve aralık 2025 sonuçları">

        <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
          <p className="text-sm font-semibold text-blue-800 mb-2">Neden Gruplandırma?</p>
          <p className="text-sm text-blue-700 leading-relaxed">
            28 bayiyi tek bir model altında tahmin etmek, küçük pazarların büyük pazarların
            istatistiğiyle ezilmesine yol açar. İstanbul'daki 7 bayi ile Sivas'taki 1 bayi
            aynı mevsimsel ritmi paylaşmaz: büyük şehirlerde Aralık patlaması daha keskin,
            küçük pazarlarda daha yumuşaktır. Gruplandırma bu farklı ritimleri yakalamayı sağlar.
          </p>
          <p className="text-sm text-blue-700 leading-relaxed mt-2">
            <strong>Kriter:</strong> TÜİK Aralık 2024 araç stoku bazlı il catchment payı.
            İstanbul+Ankara+İzmir+Bursa birlikte Türkiye araç stoğunun ~%45'ini oluşturur.
            Bu dört il, pazar dinamiği ve bayi yoğunluğu açısından homojen bir grup oluşturur.
          </p>
        </div>

        {/* Tier kartları */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(['A', 'B', 'C'] as const).map(tier => {
            const t = aralik_tahmin.tier_ozet.find(x => x.tier === tier)
            const s = TIER_STYLE[tier]
            const bayiSayisi = Object.values(bayi_aylik_hedefler.senaryo_10000).filter(b => b.tier === tier).length
            return (
              <div key={tier} className={`rounded-xl border p-5 ${s.light}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${s.badge}`}>Tier {tier}</span>
                  <span className={`text-xs font-semibold ${s.text}`}>{TIER_ACIKLAMA[tier]}</span>
                </div>
                <div className="space-y-1.5 mb-4">
                  {TIER_ILLER[tier].map(il => (
                    <span key={il} className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${s.light} ${s.text} border border-current/20 mr-1 mb-1`}>
                      {il}
                    </span>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-2 text-center border-t border-current/10 pt-3">
                  <div>
                    <p className="text-xs text-slate-500">Bayi sayısı</p>
                    <p className={`text-xl font-bold ${s.text}`}>{bayiSayisi}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Ara'25 MAPE</p>
                    <p className={`text-xl font-bold ${
                      t == null ? 'text-slate-400' :
                      t.mape == null ? 'text-slate-400' :
                      t.mape < 12 ? 'text-green-600' :
                      t.mape < 18 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {t?.mape != null ? `%${t.mape.toFixed(1)}` : '—'}
                    </p>
                  </div>
                </div>
                {t && (
                  <div className="grid grid-cols-3 gap-1 text-center mt-3 text-xs">
                    <div>
                      <p className="text-slate-400">SI (Ara)</p>
                      <p className={`font-mono font-semibold ${s.text}`}>{t.si.toFixed(3)}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">Trend</p>
                      <p className={`font-mono font-semibold ${s.text}`}>{t.trend.toFixed(3)}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">Son12 ort</p>
                      <p className={`font-mono font-semibold ${s.text}`}>{t.son12_ort.toFixed(0)}</p>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Aralık sonuçları */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">
            Aralık 2025 Tahmin Sonuçları (Yeni Tier Sistemi)
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <Karti baslik="Tahmin" deger={aralik_tahmin.ozet.toplam_tahmin.toLocaleString('tr')} alt="araç" renk="bg-blue-50 border-blue-200" />
            <Karti baslik="Gerçek" deger={aralik_tahmin.ozet.toplam_gercek.toLocaleString('tr')} alt="araç (Ara 2025)" renk="bg-white border-slate-200" />
            <Karti baslik="MAPE" deger={`%${aralik_tahmin.ozet.mape.toFixed(2)}`} alt="mutlak yüzde hata" renk={aralik_tahmin.ozet.mape < 10 ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'} />
            <Karti baslik="Hata" deger={Math.abs(aralik_tahmin.ozet.toplam_gercek - aralik_tahmin.ozet.toplam_tahmin).toString()} alt="araç farkı" renk="bg-white border-slate-200" />
          </div>
          <div className="bg-slate-50 rounded-lg p-4 text-xs text-slate-600 leading-relaxed">
            <strong>SI (Seasonal Index)</strong> nedir? Aralık ayının yıllık ortalamaya oranı.
            SI = 1.32 → Aralık, yılın ortalamasından %32 daha yüksek satış ayıdır.
            Tier A'nın SI'sı Tier C'den farklıdır çünkü büyük şehirlerde yıl sonu alımları
            (vergi, plaka sonu vb.) daha belirgindir.
            <br className="mt-1" />
            <strong className="text-slate-700">Trend çarpanı</strong> = son 6 ay ort. / önceki 6 ay ort.
            Tüm tierlerde 1.27–1.35 aralığında çıkması, markanın güçlü büyüme trendinde olduğunu gösterir.
          </div>
        </div>
      </Bolum>

      {/* ─────────────────────────────────────────────────────── */}
      {/* BÖLÜM 3 — AYLIK BAYİ MODEL HEDEFLERİ */}
      {/* ─────────────────────────────────────────────────────── */}
      <Bolum no="3" baslik="Aylık Bayi × Model Hedefleri: Nasıl Türetilir?" alt="Yıllık → Aylık → Model hiyerarşisi ve collaborative filtering">

        {/* Metodoloji adımları */}
        <div className="space-y-4">

          {/* Hiyerarşi diyagramı */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-7 text-white">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-5">
              Top-Down Hiyerarşik Ayrıştırma
            </p>
            <div className="flex flex-col md:flex-row items-start md:items-center gap-3 text-sm">
              {[
                ['Yıllık Toplam', '10.000 araç · 2026 yıllık hedefi', 'bg-blue-600'],
                ['→'],
                ['Aylık Toplam', 'Yıllık hedef × mevsimsel indeks (SI)', 'bg-indigo-600'],
                ['→'],
                ['Bayi Payı', 'Aylık toplam × bayinin hedef payı (target_pay)', 'bg-violet-600'],
                ['→'],
                ['Model Hedefi', 'Bayi aylık hedefi × bayinin tarihsel model satış oranı', 'bg-purple-600'],
              ].map((item, i) =>
                item.length === 1 ? (
                  <span key={i} className="text-slate-400 text-lg hidden md:block">→</span>
                ) : (
                  <div key={item[0]} className={`flex-1 rounded-xl p-3 ${item[2]}`}>
                    <p className="font-bold text-white text-xs">{item[0]}</p>
                    <p className="text-white/70 text-xs mt-1">{item[1]}</p>
                  </div>
                )
              )}
            </div>
          </div>

          {/* 3 adım */}
          <div className="grid grid-cols-1 gap-4">
            {[
              {
                adim: 'Adım 1 — Yıllık → Aylık (Mevsimsel Ayrıştırma)',
                yontem: 'Multiplicative Seasonal Decomposition',
                aciklama: `Her ayın hedefi = Yıllık hedef × SI(tier, ay) / Σ SI  formülüyle bulunur.
SI değerleri 2024–2025 satış verisinden hesaplanır: SI(ay) = o ayın ortalama satışı / yıllık aylık ortalama.
Tier bazlı SI kullanılır çünkü İstanbul bayilerinin Aralık'taki mevsimsel sıçraması, Sivas bayisinin iki katıdır.
Mart'a ek ×1.11 lansman boostı uygulanır (B segmenti Mart 2024/2025 pay analizi: 1 + (0.557−0.445) = 1.112).`,
                kod: 'aylik_hedef(D, m) = yillik_hedef(D) × SI(tier(D), m) / Σ_m SI',
                okunus: 'Bayi D\'nin m. ay hedefi = D\'nin yıllık hedefi × D\'nin tier grubuna ait m. ayın mevsimsel indeksi ÷ tüm aylardaki SI değerlerinin toplamı',
              },
              {
                adim: 'Adım 2 — Bayi Payı (Hibrit MCDM Formülü)',
                yontem: 'Multi-Criteria Decision Making — Ağırlıklı Pazar Payı',
                aciklama: `Yıllık bayi hedefi, pazar kapasitesi bazlı hibrit formülle belirlenir (bkz. Pazar Hedefleri sayfası).
target_pay(D) = 0.5 × brand_pay_2025(D) + 0.5 × (catchment_pay(il(D)) / n_bayis_in_il(D))
Bu pay, tüm bayiler normalize edilerek toplam = %100 yapılır.
Her aylık model toplamını bu pay oranında bayi bazına indirgemek mümkündür.`,
                kod: 'target_pay(D) = 0.5 × brand_pay_2025 + 0.5 × (catchment / n_il)',
                okunus: 'Bayi D\'nin hedef payı = %50 × bayinin 2025\'teki marka satış penetrasyonu + %50 × (bayinin bulunduğu ilin araç stok çekim alanı payı ÷ o ildeki bayi sayısı)',
              },
              {
                adim: 'Adım 3 — Model Dağılımı (Collaborative Filtering)',
                yontem: 'Tarihsel Model Karışımı (Item-Based Collaborative Filtering)',
                aciklama: `Her bayinin geçmiş 12 aydaki model tercih profili çıkarılır:
mix(D, M) = satış(D, M) / toplam_satış(D) — bayinin son 12 ayda M modelini satma oranı.
Bu profil, aylık hedefe uygulanarak model bazlı hedef üretilir.
Yeni bayilerde (satış verisi olmayan) tier ortalaması kullanılır (%60 ağırlık, muhafazakâr başlangıç).
Bu yaklaşım collaborative filtering mantığına benzer: benzer profilden bilgi taşıma.`,
                kod: 'model_hedef(D, M, m) = aylik_hedef(D, m) × mix(D, M)',
                okunus: 'Bayi D\'nin M modeli için m. ay hedefi = D\'nin o aydaki toplam araç hedefi × D\'nin son 12 ayda M modelini satma oranı',
              },
            ].map(a => (
              <div key={a.adim} className="bg-white rounded-xl border border-slate-200 p-5">
                <p className="text-sm font-bold text-slate-800 mb-1">{a.adim}</p>
                <p className="text-xs font-semibold text-blue-600 mb-3">{a.yontem}</p>
                <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line mb-3">{a.aciklama}</p>
                {/* Teknik formül */}
                <div className="bg-slate-800 rounded-lg px-4 py-2.5 mb-2">
                  <code className="text-xs font-mono text-emerald-400">{a.kod}</code>
                </div>
                {/* Açıklama */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5">
                  <p className="text-xs text-blue-600 font-semibold mb-0.5">Açıklama:</p>
                  <p className="text-xs text-blue-800 leading-relaxed">{a.okunus}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bayi seçici */}
        <div className="flex items-center gap-4 flex-wrap pt-2">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Bayi:</label>
            <select
              value={secili}
              onChange={e => setSecili(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {bayiler.map(b => {
                const bh = senaryoData[b]
                return (
                  <option key={b} value={b}>
                    {b} — {bh?.il ?? ''} {bh?.yeni_bayi ? '🆕' : ''}
                  </option>
                )
              })}
            </select>
          </div>
          {bayiHedef && (
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${TIER_STYLE[bayiHedef.tier].badge}`}>
                Tier {bayiHedef.tier}
              </span>
              {bayiHedef.yeni_bayi && (
                <span className="text-xs bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full font-medium">
                  Yeni Bayi
                </span>
              )}
              {bayiHedef.il && (
                <span className="text-xs text-slate-500">{bayiHedef.il} / {bayiHedef.ilce}</span>
              )}
            </div>
          )}
        </div>

        {/* Bayi özet kartları */}
        {bayiHedef && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Karti baslik="Yıllık Toplam" deger={bayiHedef.yillik_toplam.toLocaleString('tr')} alt="araç (2026)" renk="bg-blue-50 border-blue-200" />
            <Karti baslik="2026 Hedef Payı" deger={`%${(bayiHedef.target_pay_2026 ?? 0).toFixed(3)}`} alt="hibrit formül" renk="bg-emerald-50 border-emerald-200" />
            <Karti baslik="2025 Marka Payı" deger={bayiHedef.brand_pay_2025 != null ? `%${bayiHedef.brand_pay_2025.toFixed(3)}` : '—'} alt={bayiHedef.yeni_bayi ? 'yeni bayi' : 'geçmiş performans'} renk="bg-amber-50 border-amber-200" />
            <Karti baslik="Tier" deger={`Tier ${bayiHedef.tier}`} alt={TIER_ACIKLAMA[bayiHedef.tier]} renk={TIER_STYLE[bayiHedef.tier].light} />
          </div>
        )}

        {/* Aylık × Model matrisi */}
        {bayiHedef && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-slate-800 text-white">
                  <th className="text-left py-3 px-3 font-semibold sticky left-0 bg-slate-800 z-10 min-w-[80px]">Ay</th>
                  <th className="text-right py-3 px-3 font-semibold min-w-[70px] border-r border-slate-600">Toplam</th>
                  <th className="text-center py-3 px-3 font-semibold bg-blue-900 min-w-[90px]" colSpan={2}>A Segmenti</th>
                  <th className="text-center py-3 px-3 font-semibold bg-amber-900 min-w-[90px]" colSpan={2}>B Segmenti</th>
                </tr>
                <tr className="bg-slate-700 text-white text-xs">
                  <th className="sticky left-0 bg-slate-700 z-10" />
                  <th className="border-r border-slate-600" />
                  {BILINEN.map(m => (
                    <th key={m} className={`py-2 px-3 text-right font-semibold min-w-[65px] ${m === 'A3V02' ? 'border-r border-slate-600' : ''}`}>
                      <span className={`px-1.5 py-0.5 rounded ${MODEL_RENK[m] ?? 'bg-slate-600 text-white'}`}>{m}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bayiHedef.aylik.map((row, idx) => {
                  const isLansman = row.ay === 3
                  return (
                    <tr key={row.ay}
                      className={`border-b border-slate-100 ${
                        isLansman ? 'bg-green-50 font-semibold' :
                        idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/40'
                      }`}
                    >
                      <td className={`py-2.5 px-3 sticky left-0 z-10 font-semibold ${isLansman ? 'bg-green-50 text-green-800' : 'bg-inherit text-slate-700'}`}>
                        <div className="flex items-center gap-1">
                          {row.ay_adi}
                          {isLansman && <span className="text-xs bg-green-600 text-white px-1 rounded">LANSMAN</span>}
                        </div>
                      </td>
                      <td className={`py-2.5 px-3 text-right font-bold border-r border-slate-200 ${isLansman ? 'text-green-800' : 'text-slate-800'}`}>
                        {row.toplam.toLocaleString('tr')}
                      </td>
                      {BILINEN.map(m => {
                        const adet = row.modeller[m] ?? 0
                        const isLastA = m === 'A3V02'
                        return (
                          <td key={m}
                            className={`py-2.5 px-3 text-right font-mono ${isLastA ? 'border-r border-slate-200' : ''} ${
                              adet === 0 ? 'text-slate-300' :
                              m.startsWith('B') ? 'text-amber-700 font-semibold' :
                              'text-blue-700'
                            }`}
                          >
                            {adet > 0 ? adet : '—'}
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-bold border-t-2 border-slate-300">
                  <td className="py-3 px-3 text-slate-800 sticky left-0 bg-slate-100 z-10">YIL TOPLAMI</td>
                  <td className="py-3 px-3 text-right text-blue-700 border-r border-slate-300 font-mono">
                    {bayiHedef.yillik_toplam.toLocaleString('tr')}
                  </td>
                  {BILINEN.map(m => {
                    const adet = bayiHedef.yillik_modeller[m] ?? 0
                    const isLastA = m === 'A3V02'
                    return (
                      <td key={m} className={`py-3 px-3 text-right font-mono ${isLastA ? 'border-r border-slate-300' : ''} ${adet === 0 ? 'text-slate-300' : 'text-slate-700'}`}>
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
              </tfoot>
            </table>
          </div>
        )}

        <p className="text-xs text-slate-400">
          — = bu bayi bu modeli son 12 ayda satmamıştır (0 hedef, distribütör kararıyla eklenebilir) ·
          LANSMAN = Mart 2026 (×1.11 SI boost) · Yuvarlama nedeniyle toplam küçük fark verebilir
        </p>

        {/* Tüm bayiler özet */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Tüm Bayiler — Yıllık Hedef Özeti (10.000 araç senaryosu)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left py-2 px-2 font-semibold text-slate-600">Bayi</th>
                  <th className="text-center py-2 px-2 font-semibold">Tier</th>
                  <th className="text-left py-2 px-2 font-semibold text-slate-600">İl</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-600">Yıllık</th>
                  <th className="text-right py-2 px-2 font-semibold text-blue-700">A Seg.</th>
                  <th className="text-right py-2 px-2 font-semibold text-amber-700">B Seg.</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-500">Ocak</th>
                  <th className="text-right py-2 px-2 font-semibold text-green-700">Mart ✦</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-500">Aralık</th>
                </tr>
              </thead>
              <tbody>
                {bayiler.map(bayi => {
                  const bh = senaryoData[bayi]
                  if (!bh) return null
                  const ocak = bh.aylik.find(a => a.ay === 1)?.toplam ?? 0
                  const mart = bh.aylik.find(a => a.ay === 3)?.toplam ?? 0
                  const aralik = bh.aylik.find(a => a.ay === 12)?.toplam ?? 0
                  const isSecili = bayi === secili
                  const s = TIER_STYLE[bh.tier]
                  return (
                    <tr key={bayi}
                      onClick={() => setSecili(bayi)}
                      className={`border-b border-slate-100 cursor-pointer transition-colors ${isSecili ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                    >
                      <td className={`py-1.5 px-2 font-medium ${isSecili ? 'text-blue-700' : 'text-slate-700'}`}>
                        {bayi}
                        {bh.yeni_bayi && <span className="ml-1 text-xs bg-emerald-100 text-emerald-700 px-1 rounded">YENİ</span>}
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${s.badge}`}>{bh.tier}</span>
                      </td>
                      <td className="py-1.5 px-2 text-slate-500">{bh.il ?? ''}</td>
                      <td className="py-1.5 px-2 text-right font-bold font-mono text-slate-800">{bh.yillik_toplam.toLocaleString('tr')}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-blue-700">{(bh.yillik_segmentler['A'] ?? 0).toLocaleString('tr')}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-amber-700">{(bh.yillik_segmentler['B'] ?? 0).toLocaleString('tr')}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-slate-500">{ocak}</td>
                      <td className="py-1.5 px-2 text-right font-mono font-semibold text-green-700">{mart}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-slate-700">{aralik}</td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-slate-300 bg-slate-100 font-bold">
                  <td className="py-2 px-2 text-slate-800" colSpan={3}>TOPLAM</td>
                  <td className="py-2 px-2 text-right font-mono text-blue-700">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_toplam ?? 0), 0).toLocaleString('tr')}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-blue-700">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_segmentler['A'] ?? 0), 0).toLocaleString('tr')}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-amber-700">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.yillik_segmentler['B'] ?? 0), 0).toLocaleString('tr')}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-slate-500">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 1)?.toplam ?? 0), 0).toLocaleString('tr')}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-green-700">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 3)?.toplam ?? 0), 0).toLocaleString('tr')}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-slate-700">
                    {bayiler.reduce((s, b) => s + (senaryoData[b]?.aylik.find(a => a.ay === 12)?.toplam ?? 0), 0).toLocaleString('tr')}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            ✦ Mart = Lansman ayı · Satıra tıklayarak yukarıdaki detay matrisini görüntüleyin
          </p>
        </div>
      </Bolum>

    </div>
  )
}
