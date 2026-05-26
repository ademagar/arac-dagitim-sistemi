import { useEffect, useRef, useState } from 'react'
import * as XLSX from 'xlsx'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { Upload, CheckCircle, ChevronRight, RotateCcw, Info } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Vehicle    { chassis: string; model: string; version: string; color: string; vehicle_type: string }
interface Dealer     { name: string; code: string; active: boolean; activity: Record<string,string> }
interface BayiHedefRow { dealer: string; code: string; target: number | null }
interface AllocVehicle extends Vehicle { dealer: string }
interface SummaryRow { dealer: string; target: number; allocated: number; gap: number; fill_rate: number }

const MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']
const MONTH_TO_ACTIVITY: Record<string,string> = {
  'Ocak':'Oca.26','Şubat':'Şub.26','Mart':'Mar.26','Nisan':'Nis.26','Mayıs':'May.26',
}
const MONTH_EN: Record<string,string[]> = {
  'Ocak':['January','Current Month','Jan','1'], 'Şubat':['February','Feb','2'],
  'Mart':['March','Mar','3'], 'Nisan':['April','Apr','4'],
  'Mayıs':['May','5'], 'Haziran':['June','Jun','6'],
  'Temmuz':['July','Jul','7'], 'Ağustos':['August','Aug','8'],
  'Eylül':['September','Sep','9'], 'Ekim':['October','Oct','10'],
  'Kasım':['November','Nov','11'], 'Aralık':['December','Dec','12'],
}
const CHART_COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16']

// Model adının ilk harfi → grup (A1,A2,A3 → "A" | B1,B2 → "B")
function modelGroup(model: string) { return model.charAt(0).toUpperCase() }

function numSort(a: string, b: string) {
  return parseInt(a.match(/\d+$/)?.[0]??'0') - parseInt(b.match(/\d+$/)?.[0]??'0')
}

// ─── Allocation ───────────────────────────────────────────────────────────────
// Faz 1 — her bayiye her model grubundan (A, B, …) en az 1 araç garantisi
// Faz 2 — kalan araçlar kotaya orantılı dağıtılır; hiçbir zaman hedef aşılmaz
function allocate(
  vehicles: Vehicle[],
  targets: { dealer: string; target: number }[],
): { allocated: AllocVehicle[]; summary: SummaryRow[] } {

  const active      = targets.filter(t => t.target > 0)
  const totalTarget = active.reduce((s, t) => s + t.target, 0)
  const toDistribute = Math.min(vehicles.length, totalTarget)
  const scale        = vehicles.length < totalTarget ? vehicles.length / totalTarget : 1.0

  const pool = [...vehicles]

  // Kotalar — hiçbir zaman hedefin üzerine çıkılmaz
  const quotas = active.map(t => ({
    dealer:   t.dealer,
    target:   t.target,
    quota:    Math.min(t.target, Math.round(t.target * scale)),
    assigned: [] as Vehicle[],
  }))

  // Supply < demand → yuvarlama farkını düzelt
  if (vehicles.length < totalTarget) {
    let totalQuota = quotas.reduce((s, q) => s + q.quota, 0)
    let diff  = toDistribute - totalQuota
    quotas.sort((a,b) => b.quota - a.quota)
    let guard = quotas.length * 4
    for (let i = 0; diff !== 0 && guard-- > 0; i = (i + 1) % quotas.length) {
      if (diff > 0 && quotas[i].quota < quotas[i].target) { quotas[i].quota++; diff-- }
      else if (diff < 0 && quotas[i].quota > 0)           { quotas[i].quota--; diff++ }
    }
    quotas.sort((a,b) => numSort(a.dealer, b.dealer))
  }

  // ── Faz 1: her model grubu için minimum 1 araç ────────────────────────────
  // Gruplar model adının ilk harfinden otomatik türetilir (A→A grubu, B→B grubu)
  const uniqueGroups = [...new Set(pool.map(v => modelGroup(v.model)))].sort()

  // Küçük kotadan büyüğe işle → küçük bayiler dezavantajlı kalmasın
  const byQuota = [...quotas].sort((a,b) => a.quota - b.quota)
  for (const q of byQuota) {
    for (const grp of uniqueGroups) {
      if (q.quota <= 0) break
      const idx = pool.findIndex(v => modelGroup(v.model) === grp)
      if (idx !== -1) {
        q.assigned.push(pool.splice(idx, 1)[0])
        q.quota--
      }
    }
  }

  // ── Faz 2: kalan havuzu kotaya orantılı dağıt ─────────────────────────────
  const byType: Record<string, Vehicle[]> = {}
  pool.forEach(v => { if (!byType[v.vehicle_type]) byType[v.vehicle_type] = []; byType[v.vehicle_type].push(v) })
  const types = Object.keys(byType)
  const initCount: Record<string,number> = {}
  types.forEach(t => { initCount[t] = byType[t].length })
  const initTotal = pool.length

  quotas.forEach(q => {
    if (q.quota <= 0) return
    let remaining = q.quota
    types.forEach(type => {
      if (remaining <= 0 || byType[type].length === 0) return
      const share = Math.min(
        Math.round(q.quota * (initCount[type] || 0) / (initTotal || 1)),
        byType[type].length,
        remaining,
      )
      if (share <= 0) return
      q.assigned.push(...byType[type].splice(0, share))
      remaining -= share
    })
    for (const type of types) {
      if (remaining <= 0) break
      const take = Math.min(remaining, byType[type].length)
      if (take > 0) { q.assigned.push(...byType[type].splice(0, take)); remaining -= take }
    }
  })

  const allocated: AllocVehicle[] = []
  const summary: SummaryRow[]    = []
  quotas.forEach(q => {
    q.assigned.forEach(v => allocated.push({ ...v, dealer: q.dealer }))
    const alloc = q.assigned.length
    summary.push({ dealer: q.dealer, target: q.target, allocated: alloc, gap: alloc - q.target,
      fill_rate: q.target > 0 ? Math.round(alloc / q.target * 1000) / 10 : 0 })
  })

  return { allocated, summary: summary.sort((a,b) => numSort(a.dealer, b.dealer)) }
}

// ─── UI helpers ───────────────────────────────────────────────────────────────
function Steps({ active }: { active: number }) {
  const steps = ['Envanter Yükle', 'Bayi Hedefleri', 'Sonuçlar']
  return (
    <div className="flex items-center gap-0 mb-8 flex-wrap gap-y-2">
      {steps.map((s, i) => {
        const done = i < active; const current = i === active
        return (
          <div key={s} className="flex items-center">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              current ? 'bg-blue-600 text-white' : done ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'
            }`}>
              {done ? <CheckCircle size={14}/> : <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs border-current">{i+1}</span>}
              {s}
            </div>
            {i < steps.length - 1 && <ChevronRight size={16} className="text-slate-300 mx-1"/>}
          </div>
        )
      })}
    </div>
  )
}

function TabBar({ tabs, active, onChange }: { tabs: string[]; active: number; onChange: (i: number) => void }) {
  return (
    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit flex-wrap mb-5">
      {tabs.map((t, i) => (
        <button key={t} onClick={() => onChange(i)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${active===i?'bg-white text-slate-900 shadow-sm':'text-slate-500 hover:text-slate-700'}`}>
          {t}
        </button>
      ))}
    </div>
  )
}

const GROUP_COLORS: Record<string,{bg:string;text:string;pill:string}> = {
  A: { bg:'bg-blue-50',   text:'text-blue-700',   pill:'bg-blue-100 text-blue-700'   },
  B: { bg:'bg-purple-50', text:'text-purple-700', pill:'bg-purple-100 text-purple-700'},
  C: { bg:'bg-green-50',  text:'text-green-700',  pill:'bg-green-100 text-green-700'  },
  D: { bg:'bg-orange-50', text:'text-orange-700', pill:'bg-orange-100 text-orange-700'},
}
function grpStyle(g: string) { return GROUP_COLORS[g] ?? { bg:'bg-slate-50', text:'text-slate-700', pill:'bg-slate-100 text-slate-700' } }

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Dagitim() {
  const [step, setStep]             = useState(0)
  const [month, setMonth]           = useState('Ocak')
  const [fileName, setFileName]     = useState('')
  const [parseError, setError]      = useState('')
  const [rawPool, setRawPool]       = useState<Vehicle[]>([])
  const [allDealers, setAllDealers] = useState<Dealer[]>([])
  const [dealers, setDealers]       = useState<Dealer[]>([])
  const [bayiHedef, setBayiHedef]   = useState<Record<string, BayiHedefRow[]>>({})
  const [targets, setTargets]       = useState<Record<string,number>>({})
  const [allocated, setAllocated]   = useState<AllocVehicle[]>([])
  const [summary, setSummary]       = useState<SummaryRow[]>([])
  const [resultTab, setResultTab]   = useState(0)
  const [modelFilter, setMF]        = useState('')
  const [dealerFilter, setDF]       = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const base = import.meta.env.BASE_URL
    fetch(`${base}data/dealers.json`).then(r => r.json()).then(setAllDealers)
    fetch(`${base}data/bayi-hedefleri.json`).then(r => r.json()).then(setBayiHedef)
  }, [])

  useEffect(() => {
    if (!allDealers.length) return
    const actCol = MONTH_TO_ACTIVITY[month]
    const active = actCol
      ? allDealers.filter(d => d.activity[actCol] === 'AKTİF')
      : allDealers.filter(d => d.active)
    setDealers(active)
    setTargets(prev => {
      const t: Record<string,number> = {}
      active.forEach(d => { t[d.name] = prev[d.name] ?? 0 })
      return t
    })
  }, [month, allDealers])

  function handleFile(file: File) {
    setError('')
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data  = new Uint8Array(e.target!.result as ArrayBuffer)
        const wb    = XLSX.read(data, { type: 'array' })
        const ws    = wb.Sheets[wb.SheetNames[0]]
        const rows  = XLSX.utils.sheet_to_json<Record<string,string>>(ws, { defval: '' })
        const norm  = rows.map(r => { const o: Record<string,string> = {}; Object.entries(r).forEach(([k,v]) => { o[k.trim()]=String(v).trim() }); return o })
        const variants = MONTH_EN[month] ?? [month]
        const pool = norm.filter(r =>
          r['Dealer Code Processing'] === 'CENT-STOCK' &&
          r['Dispatchable'] === 'Y' &&
          variants.some(mv => r['Month Number']?.toLowerCase() === mv.toLowerCase())
        )
        if (pool.length === 0) {
          const found = [...new Set(norm.map(r => r['Month Number']))].filter(Boolean).slice(0,8).join(', ')
          setError(`Filtre sonucu boş. 'CENT-STOCK' + 'Dispatchable=Y' + ay='${month}' bulunamadı.\nDosyadaki Month Number değerleri: ${found || '(bulunamadı)'}`)
          return
        }
        const vehicles: Vehicle[] = pool.map(r => ({
          chassis: r['Long Chassis No'] ?? r['Long Chassis'] ?? r['Chassis No'] ?? r['Chassis Number'] ?? r['VIN'] ?? r['VIN No'] ?? '',
          model:   r['Model Description'] ?? '',
          version: r['Vehicle Version']   ?? '',
          color:   r['Exterior Color']    ?? '',
          vehicle_type: `${r['Model Description']??''} / ${r['Vehicle Version']??''} / ${r['Exterior Color']??''}`,
        }))
        setRawPool(vehicles)
        setFileName(file.name)
        // Envanter özeti + kural bilgisi göster, step 0'da kal
      } catch (err) { setError(`Dosya okunamadı: ${err}`) }
    }
    reader.readAsArrayBuffer(file)
  }

  const totalTarget = Object.values(targets).reduce((s,v) => s+v, 0)
  const overSupply  = totalTarget > rawPool.length

  function confirmAndCalculate() {
    const tArr = Object.entries(targets).filter(([,v]) => v > 0).map(([dealer, target]) => ({ dealer, target }))
    const { allocated: a, summary: s } = allocate(rawPool, tArr)
    setAllocated(a); setSummary(s); setResultTab(0); setMF(''); setDF(''); setStep(2)
  }

  function reset() {
    setStep(0); setRawPool([]); setFileName(''); setError('')
    const t: Record<string,number> = {}; dealers.forEach(d => { t[d.name]=0 }); setTargets(t)
    setAllocated([]); setSummary([])
    if (fileRef.current) fileRef.current.value = ''
  }

  // ── Model grubu özeti (A→A1,A2,A3 | B→B1) ────────────────────────────────
  const groupSummary = (() => {
    const map: Record<string,{ models: Set<string>; count: number }> = {}
    rawPool.forEach(v => {
      const g = modelGroup(v.model)
      if (!map[g]) map[g] = { models: new Set(), count: 0 }
      map[g].models.add(v.model)
      map[g].count++
    })
    return Object.entries(map).sort(([a],[b]) => a.localeCompare(b)).map(([grp, d]) => ({
      grp,
      models: [...d.models].sort(),
      count: d.count,
    }))
  })()

  // Minimum gereksinim: bayi sayısı × grup sayısı
  const minRequired = dealers.length * groupSummary.length

  // ── Inventory summary ─────────────────────────────────────────────────────
  const invByType = Object.values(
    rawPool.reduce<Record<string,{model:string;version:string;color:string;count:number}>>((acc,v) => {
      if (!acc[v.vehicle_type]) acc[v.vehicle_type] = { model:v.model, version:v.version, color:v.color, count:0 }
      acc[v.vehicle_type].count++; return acc
    }, {})
  ).sort((a,b) => b.count - a.count)
  const invModels = [...new Set(rawPool.map(v=>v.model))].sort()
  const modelChart = invModels.map(m => ({ model:m, adet: rawPool.filter(v=>v.model===m).length })).sort((a,b)=>b.adet-a.adet)

  // ── Results derived ───────────────────────────────────────────────────────
  const allModels   = [...new Set(allocated.map(v=>v.model))].sort()
  const allDealersR = [...new Set(allocated.map(v=>v.dealer))].sort(numSort)

  const vehicleRows = allocated.filter(v =>
    (!modelFilter  || v.model  === modelFilter) &&
    (!dealerFilter || v.dealer === dealerFilter)
  )

  // A/B kural karşılanma durumu per dealer
  const groupsInResult = [...new Set(allocated.map(v => modelGroup(v.model)))].sort()
  const dealerGroupCheck = allDealersR.reduce<Record<string, Record<string,boolean>>>((acc, dealer) => {
    const dvs = allocated.filter(v => v.dealer === dealer)
    acc[dealer] = {}
    groupsInResult.forEach(g => { acc[dealer][g] = dvs.some(v => modelGroup(v.model) === g) })
    return acc
  }, {})
  const allGroupsSatisfied = (dealer: string) =>
    groupsInResult.every(g => dealerGroupCheck[dealer]?.[g])

  const satisfiedCount = allDealersR.filter(allGroupsSatisfied).length

  const stackedData = allDealersR.map(dealer => {
    const row: Record<string,unknown> = { dealer }
    allModels.forEach(m => { row[m] = allocated.filter(v=>v.dealer===dealer && v.model===m).length })
    return row
  })
  const modelSummary = allModels.map(m => ({
    model: m, total: allocated.filter(v=>v.model===m).length,
    dealers: allDealersR.map(d => ({ dealer:d, count: allocated.filter(v=>v.dealer===d && v.model===m).length })).filter(x=>x.count>0),
  }))

  // ─── STEP 0-A: Yükleme formu ──────────────────────────────────────────────
  const StepUploadForm = (
    <div className="max-w-2xl space-y-5">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-2">Dağıtım Ayı</label>
          <select value={month} onChange={e => setMonth(e.target.value)}
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white w-48">
            {MONTHS.map(m => <option key={m}>{m}</option>)}
          </select>
          {MONTH_TO_ACTIVITY[month] && (
            <p className="text-xs text-slate-400 mt-1">{dealers.length} aktif bayi ({MONTH_TO_ACTIVITY[month]})</p>
          )}
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-2">Envanter Dosyası</label>
          <p className="text-xs text-slate-500 mb-3">
            Excel (.xlsx) veya CSV — Gerekli sütunlar:{' '}
            {['Dealer Code Processing','Dispatchable','Month Number','Long Chassis No','Model Description','Vehicle Version','Exterior Color'].map(c => (
              <code key={c} className="bg-slate-100 px-1 rounded text-xs mx-0.5">{c}</code>
            ))}
          </p>
          <label className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-slate-300 rounded-xl p-10 cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
            <Upload size={28} className="text-slate-400"/>
            <span className="text-sm text-slate-500">Dosyayı sürükleyin veya seçin</span>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}/>
          </label>
        </div>
        {parseError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 whitespace-pre-wrap">{parseError}</div>
        )}
      </div>
    </div>
  )

  // ─── STEP 0-B: Envanter özeti + kural bilgisi ─────────────────────────────
  const StepInventorySummary = (
    <div className="space-y-5">
      {/* Başarı banner */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-green-800">{fileName}</p>
          <p className="text-xs text-green-600 mt-0.5">{rawPool.length} araç · {month} · CENT-STOCK · Dispatchable=Y</p>
        </div>
        <button onClick={reset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-500">
          <RotateCcw size={13}/> Farklı Dosya
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {([
          ['Toplam Araç',  rawPool.length,                        'text-blue-600'],
          ['Farklı Tip',   invByType.length,                      'text-slate-900'],
          ['Model Sayısı', invModels.length,                      'text-slate-900'],
          ['Farklı Renk',  new Set(rawPool.map(v=>v.color)).size, 'text-slate-900'],
        ] as [string, number, string][]).map(([l,v,c]) => (
          <div key={l} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">{l}</p>
            <p className={`text-2xl font-bold ${c}`}>{v}</p>
          </div>
        ))}
      </div>

      {/* Dağıtım Kuralı */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-3">
          <Info size={15} className="text-blue-500 shrink-0"/>
          <h3 className="text-sm font-semibold text-slate-800">Uygulanan Dağıtım Kuralı</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Her bayiye önce her model grubundan <span className="font-semibold text-slate-700">en az 1 araç</span> ayrılır, ardından kalan araçlar kotaya orantılı dağıtılır.
        </p>

        <div className="flex flex-wrap gap-3 mb-4">
          {groupSummary.map(({ grp, models, count }) => {
            const s = grpStyle(grp)
            return (
              <div key={grp} className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${s.bg} border-current/10`}>
                <span className={`text-2xl font-black ${s.text}`}>{grp}</span>
                <div>
                  <p className="text-xs font-medium text-slate-700">{models.join(', ')}</p>
                  <p className="text-xs text-slate-400">{count} araç</p>
                </div>
              </div>
            )
          })}
        </div>

        <div className={`text-xs rounded-lg px-4 py-2.5 flex items-center gap-2 ${
          minRequired <= rawPool.length
            ? 'bg-green-50 text-green-700'
            : 'bg-amber-50 text-amber-700'
        }`}>
          {minRequired <= rawPool.length ? '✓' : '⚠'}
          <span>
            <strong>{dealers.length} bayi × {groupSummary.length} grup = {minRequired} araç</strong> minimum ayrılacak
            {minRequired > rawPool.length && ` — havuzda yalnızca ${rawPool.length} araç var, bazı bayilerde tüm gruplar karşılanamayabilir`}
          </span>
        </div>
      </div>

      {/* Model dağılımı */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Model Dağılımı</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={modelChart} layout="vertical" margin={{ left:20, right:40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9"/>
              <XAxis type="number" tick={{ fontSize:11 }}/>
              <YAxis type="category" dataKey="model" tick={{ fontSize:12 }} width={35}/>
              <Tooltip/>
              <Bar dataKey="adet" name="Araç" radius={[0,4,4,0]}>
                {modelChart.map((_,i) => <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]}/>)}
                <LabelList dataKey="adet" position="right" style={{ fontSize:11 }}/>
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="px-4 py-3 border-b border-slate-200">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Araç Havuzu ({invByType.length} tip)</h3>
          </div>
          <div className="overflow-auto max-h-52">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
                <tr>
                  {['Model','Versiyon','Renk','Adet'].map(h => (
                    <th key={h} className={`px-3 py-2 font-medium text-slate-500 ${h==='Adet'?'text-right':'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invByType.map((v,i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-1.5 font-medium text-slate-900">{v.model}</td>
                    <td className="px-3 py-1.5 text-slate-600">{v.version}</td>
                    <td className="px-3 py-1.5 text-slate-600">{v.color}</td>
                    <td className="px-3 py-1.5 text-right font-semibold text-blue-600">{v.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <button onClick={() => setStep(1)}
        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
        Bayi Hedeflerine Geç <ChevronRight size={16}/>
      </button>
    </div>
  )

  // ─── STEP 1: Bayi hedefleri ────────────────────────────────────────────────
  const StepTargets = (
    <div className="space-y-5">
      {/* Arz/talep barı */}
      <div className={`rounded-xl border p-4 ${overSupply?'bg-red-50 border-red-200':totalTarget>0?'bg-green-50 border-green-200':'bg-slate-50 border-slate-200'}`}>
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className={`text-3xl font-bold ${overSupply?'text-red-600':'text-blue-600'}`}>{totalTarget}</span>
            <span className="text-slate-500 text-sm ml-2">/ {rawPool.length} araç</span>
          </div>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${overSupply?'bg-red-100 text-red-700':totalTarget>0?'bg-green-100 text-green-700':'bg-slate-100 text-slate-500'}`}>
            {overSupply ? '⚠ Arz aşıldı!' : totalTarget > 0 ? '✓ Arz yeterli' : 'Henüz girilmedi'}
          </span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div className="h-2 rounded-full transition-all" style={{ width:`${Math.min(100, rawPool.length>0?totalTarget/rawPool.length*100:0)}%`, background: overSupply?'#ef4444':'#3b82f6' }}/>
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>Toplam Talep</span>
          <span>Kalan: {Math.max(0, rawPool.length-totalTarget)} araç</span>
        </div>
      </div>

      {/* Kural özeti */}
      <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
        <Info size={14} className="text-slate-400 shrink-0"/>
        <span className="text-xs text-slate-600">
          Her bayiye{' '}
          {groupSummary.map(({ grp }, i) => (
            <span key={grp}>
              {i > 0 && ' + '}
              <span className={`font-semibold ${grpStyle(grp).text}`}>1 {grp} grubu</span>
            </span>
          ))}
          {' '}araç önce ayrılır, kalanlar orantılı dağıtılır.
        </span>
      </div>

      {/* Aksiyonlar */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <p className="text-sm font-medium text-slate-700">Bayi başına aylık hedef girin — {dealers.length} aktif bayi ({month})</p>
        <div className="flex gap-2 flex-wrap">
          {bayiHedef[month] && (
            <button
              onClick={() => {
                const rows = bayiHedef[month]
                setTargets(prev => {
                  const t = { ...prev }
                  rows.forEach(r => { if (r.target !== null && t[r.dealer] !== undefined) t[r.dealer] = r.target })
                  return t
                })
              }}
              className="text-xs bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 px-3 py-1.5 rounded-lg font-medium transition-colors"
            >
              📋 {month} Hedeflerini Yükle
            </button>
          )}
          <button onClick={() => { const t: Record<string,number>={}; dealers.forEach(d=>{t[d.name]=0}); setTargets(t) }}
            className="text-xs text-slate-400 hover:text-red-500 flex items-center gap-1">
            <RotateCcw size={12}/> Sıfırla
          </button>
        </div>
      </div>

      {/* Bayi grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {[...dealers].sort((a,b) => numSort(a.name,b.name)).map(d => {
          const val = targets[d.name] ?? 0
          return (
            <div key={d.name} className={`bg-white rounded-xl border p-3 transition-colors ${val>0?'border-blue-300 bg-blue-50':'border-slate-200'}`}>
              <p className="text-xs font-semibold text-slate-700 truncate">{d.name}</p>
              <p className="text-xs text-slate-400 font-mono mb-2">{d.code}</p>
              <input type="number" min={0} max={500}
                value={val===0?'':val} placeholder="0"
                onChange={e => setTargets(prev => ({ ...prev, [d.name]: Math.max(0, parseInt(e.target.value)||0) }))}
                className="w-full text-center text-lg font-bold border border-slate-200 rounded-lg py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="text-xs text-slate-400 text-center mt-1">araç/ay</p>
            </div>
          )
        })}
      </div>

      <div className="flex gap-3">
        <button onClick={() => setStep(0)} className="px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50">
          ← Geri
        </button>
        <button
          disabled={totalTarget===0 || overSupply}
          onClick={confirmAndCalculate}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2"
        >
          <CheckCircle size={16}/> Onayla ve Dağıtımı Hesapla
        </button>
      </div>
    </div>
  )

  // ─── STEP 2: Sonuçlar ─────────────────────────────────────────────────────
  const totalAllocated = allocated.length
  const fillRate = rawPool.length > 0 ? totalAllocated / rawPool.length * 100 : 0

  const StepResults = (
    <div className="space-y-5">
      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {([
          ['Envanterdeki Araç',  rawPool.length,            'text-slate-900'],
          ['Atanan Araç',        totalAllocated,            'text-blue-600'],
          ['Envanter Kullanımı', `%${fillRate.toFixed(1)}`, fillRate>=85?'text-green-600':'text-amber-600'],
          ['Aktif Bayi',         summary.length,            'text-slate-900'],
        ] as [string, string|number, string][]).map(([l,v,c]) => (
          <div key={l} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">{l}</p>
            <p className={`text-2xl font-bold ${c}`}>{v}</p>
          </div>
        ))}
      </div>

      {/* Kural özeti */}
      <div className={`flex items-center gap-3 rounded-xl px-4 py-3 text-xs border ${
        satisfiedCount === allDealersR.length
          ? 'bg-green-50 border-green-200 text-green-700'
          : 'bg-amber-50 border-amber-200 text-amber-700'
      }`}>
        {satisfiedCount === allDealersR.length ? <CheckCircle size={14}/> : <Info size={14}/>}
        <span>
          Model grubu kuralı: <strong>{satisfiedCount}/{allDealersR.length}</strong> bayide tüm gruplar karşılandı
          {satisfiedCount < allDealersR.length && ' — kalan bayilerde arz yetersiz kaldı'}
        </span>
      </div>

      <TabBar tabs={['Dağıtım Tablosu','Bayi Özeti','Model Dağılımı']} active={resultTab} onChange={setResultTab}/>

      {/* ── TAB 0: Dağıtım Tablosu ── */}
      {resultTab === 0 && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap gap-4 items-end">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Model</label>
              <select value={modelFilter} onChange={e=>setMF(e.target.value)}
                className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white">
                <option value="">Tümü</option>
                {allModels.map(m=><option key={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Bayi</label>
              <select value={dealerFilter} onChange={e=>setDF(e.target.value)}
                className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white">
                <option value="">Tümü</option>
                {allDealersR.map(d=><option key={d}>{d}</option>)}
              </select>
            </div>
            {(modelFilter||dealerFilter) && (
              <button onClick={()=>{setMF('');setDF('')}} className="text-xs text-blue-500 hover:text-blue-700">Filtreyi Temizle</button>
            )}
            <p className="text-xs text-slate-400 ml-auto">{vehicleRows.length} araç gösteriliyor</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-auto max-h-[520px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs w-8">#</th>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs">Long Chassis No</th>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs">Model</th>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs">Versiyon</th>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs">Renk</th>
                    <th className="px-4 py-2.5 text-left font-medium text-slate-500 text-xs">Gönderildiği Bayi</th>
                  </tr>
                </thead>
                <tbody>
                  {vehicleRows.map((v, i) => {
                    const grp = modelGroup(v.model)
                    const s   = grpStyle(grp)
                    return (
                      <tr key={i} className={`border-b border-slate-100 hover:bg-slate-50 ${i%2===0?'':'bg-slate-50/30'}`}>
                        <td className="px-4 py-2 text-slate-400 text-xs">{i+1}</td>
                        <td className="px-4 py-2 font-mono text-xs text-slate-700 whitespace-nowrap">{v.chassis||'—'}</td>
                        <td className="px-4 py-2">
                          <span className={`font-semibold text-slate-900`}>{v.model}</span>
                          <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded font-bold ${s.pill}`}>{grp}</span>
                        </td>
                        <td className="px-4 py-2 text-slate-600">{v.version}</td>
                        <td className="px-4 py-2 text-slate-600">{v.color}</td>
                        <td className="px-4 py-2">
                          <span className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full font-medium">
                            {v.dealer}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 1: Bayi Özeti ── */}
      {resultTab === 1 && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {summary.map(s => {
              const ok  = s.fill_rate >= 85
              const chk = dealerGroupCheck[s.dealer] ?? {}
              const allOk = groupsInResult.every(g => chk[g])
              return (
                <div key={s.dealer} className="bg-white rounded-xl border border-slate-200 shadow-sm p-3">
                  <div className="flex items-start justify-between gap-1 mb-1">
                    <p className="text-xs font-semibold text-slate-700">{s.dealer}</p>
                    <div className="flex gap-1 shrink-0">
                      {groupsInResult.map(g => (
                        <span key={g} className={`text-xs px-1 py-0.5 rounded font-bold ${chk[g] ? grpStyle(g).pill : 'bg-slate-100 text-slate-400'}`}>
                          {g}{chk[g]?'✓':'✗'}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-end gap-1 mb-1">
                    <span className="text-2xl font-bold text-blue-600">{s.allocated}</span>
                    <span className="text-slate-400 text-sm mb-0.5">/ {s.target}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 mb-1">
                    <div className="h-1.5 rounded-full" style={{ width:`${Math.min(100,s.fill_rate)}%`, background: ok?'#22c55e':'#f59e0b' }}/>
                  </div>
                  <span className={`text-xs font-medium ${ok?'text-green-600':'text-amber-600'}`}>%{s.fill_rate.toFixed(1)}</span>
                  {!allOk && <span className="ml-2 text-xs text-amber-500">eksik grup</span>}
                </div>
              )
            })}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Hedef vs Atanan</h3>
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={summary} margin={{ left:0, right:10, bottom:60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9"/>
                <XAxis dataKey="dealer" tick={{ fontSize:10 }} angle={-45} textAnchor="end" interval={0}/>
                <YAxis tick={{ fontSize:11 }}/>
                <Tooltip/><Legend/>
                <Bar dataKey="target"    name="Hedef"  fill="#cbd5e1" radius={[4,4,0,0]}/>
                <Bar dataKey="allocated" name="Atanan" radius={[4,4,0,0]}>
                  {summary.map((s,i) => <Cell key={i} fill={s.fill_rate>=85?'#22c55e':'#f59e0b'}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-left">Bayi</th>
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-right">Hedef</th>
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-right">Atanan</th>
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-right">Fark</th>
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-center">Doluluk</th>
                    <th className="px-4 py-2.5 font-medium text-slate-500 text-xs text-center">Gruplar</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.map(s => {
                    const chk = dealerGroupCheck[s.dealer] ?? {}
                    return (
                      <tr key={s.dealer} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-medium text-slate-900">{s.dealer}</td>
                        <td className="px-4 py-2.5 text-right text-slate-600">{s.target}</td>
                        <td className="px-4 py-2.5 text-right font-bold text-blue-600">{s.allocated}</td>
                        <td className={`px-4 py-2.5 text-right font-semibold ${s.gap>=0?'text-green-600':'text-red-600'}`}>
                          {s.gap>=0?'+':''}{s.gap}
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.fill_rate>=85?'bg-green-100 text-green-700':'bg-amber-100 text-amber-700'}`}>
                            %{s.fill_rate.toFixed(1)}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-1 justify-center">
                            {groupsInResult.map(g => (
                              <span key={g} className={`text-xs px-1.5 py-0.5 rounded font-bold ${chk[g]?grpStyle(g).pill:'bg-slate-100 text-slate-400'}`}>
                                {g}{chk[g]?'✓':'✗'}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: Model Dağılımı ── */}
      {resultTab === 2 && (
        <div className="space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Bayi × Model Dağılımı</h3>
            <ResponsiveContainer width="100%" height={380}>
              <BarChart data={stackedData} margin={{ left:0, right:10, bottom:60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9"/>
                <XAxis dataKey="dealer" tick={{ fontSize:10 }} angle={-45} textAnchor="end" interval={0}/>
                <YAxis tick={{ fontSize:11 }}/><Tooltip/><Legend/>
                {allModels.map((m,i) => (
                  <Bar key={m} dataKey={m} stackId="a" fill={CHART_COLORS[i%CHART_COLORS.length]}/>
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {modelSummary.map((ms, mi) => (
              <div key={ms.model} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{ms.model}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${grpStyle(modelGroup(ms.model)).pill}`}>
                      {modelGroup(ms.model)}
                    </span>
                  </div>
                  <span className="text-2xl font-bold" style={{ color: CHART_COLORS[mi%CHART_COLORS.length] }}>{ms.total}</span>
                </div>
                <div className="space-y-1.5">
                  {ms.dealers.sort((a,b) => numSort(a.dealer,b.dealer)).map(d => (
                    <div key={d.dealer} className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-20 shrink-0">{d.dealer}</span>
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full" style={{ width:`${ms.total>0?d.count/ms.total*100:0}%`, background: CHART_COLORS[mi%CHART_COLORS.length] }}/>
                      </div>
                      <span className="text-xs font-semibold text-slate-700 w-6 text-right">{d.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-600">Model × Bayi Pivot</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="px-3 py-2.5 text-left font-medium text-slate-500">Bayi</th>
                    {allModels.map(m => (
                      <th key={m} className="px-3 py-2.5 text-right font-medium text-slate-500">
                        {m}
                        <span className={`ml-1 text-xs px-1 py-0.5 rounded font-bold ${grpStyle(modelGroup(m)).pill}`}>{modelGroup(m)}</span>
                      </th>
                    ))}
                    <th className="px-3 py-2.5 text-right font-semibold text-slate-600">Toplam</th>
                  </tr>
                </thead>
                <tbody>
                  {allDealersR.map(dealer => {
                    const total = allocated.filter(v=>v.dealer===dealer).length
                    return (
                      <tr key={dealer} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium text-slate-800">{dealer}</td>
                        {allModels.map(m => {
                          const cnt = allocated.filter(v=>v.dealer===dealer && v.model===m).length
                          return (
                            <td key={m} className="px-3 py-2 text-right">
                              {cnt > 0 ? <span className="font-semibold text-slate-800">{cnt}</span> : <span className="text-slate-300">—</span>}
                            </td>
                          )
                        })}
                        <td className="px-3 py-2 text-right font-bold text-blue-600">{total}</td>
                      </tr>
                    )
                  })}
                  <tr className="bg-slate-50 border-t-2 border-slate-200">
                    <td className="px-3 py-2 font-bold text-slate-700">Toplam</td>
                    {allModels.map(m => (
                      <td key={m} className="px-3 py-2 text-right font-bold text-slate-700">
                        {allocated.filter(v=>v.model===m).length}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right font-bold text-blue-700">{allocated.length}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <button onClick={() => setStep(1)} className="px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50">
          ← Hedefleri Düzenle
        </button>
        <button onClick={reset} className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50">
          <RotateCcw size={14}/> Yeni Dağıtım
        </button>
      </div>
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Dağıtım Sistemi</h1>
        <p className="text-slate-500 text-sm mt-1">Envanter yükle → hedefleri onayla → dağıtım hesapla</p>
      </div>
      <Steps active={step}/>
      {step === 0 && !fileName && StepUploadForm}
      {step === 0 &&  fileName && StepInventorySummary}
      {step === 1 && StepTargets}
      {step === 2 && StepResults}
    </div>
  )
}
