import { useEffect, useRef, useState } from 'react'
import * as XLSX from 'xlsx'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { Upload, CheckCircle, ChevronRight, RotateCcw } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────
interface VehicleRow { model: string; version: string; color: string; vehicle_type: string; quantity: number }
interface Dealer     { name: string }
interface Target     { dealer: string; target: number }
interface AllocRow   { dealer: string; model: string; version: string; color: string; quantity: number }
interface SummaryRow { dealer: string; target: number; allocated: number; gap: number; fill_rate: number }

const MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']
const MONTH_EN: Record<string,string[]> = {
  'Ocak':['January','Current Month','Jan','1'], 'Şubat':['February','Feb','2'],
  'Mart':['March','Mar','3'], 'Nisan':['April','Apr','4'],
  'Mayıs':['May','5'], 'Haziran':['June','Jun','6'],
  'Temmuz':['July','Jul','7'], 'Ağustos':['August','Aug','8'],
  'Eylül':['September','Sep','9'], 'Ekim':['October','Oct','10'],
  'Kasım':['November','Nov','11'], 'Aralık':['December','Dec','12'],
}

const CHART_COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316']

function numSort(a: string, b: string) {
  return parseInt(a.match(/\d+$/)?.[0]??'0') - parseInt(b.match(/\d+$/)?.[0]??'0')
}

// ─── Allocation engine (JS) ───────────────────────────────────────────────────
function runAllocation(pool: VehicleRow[], targets: Target[]): { rows: AllocRow[]; summary: SummaryRow[] } {
  // Build mutable inventory counts
  const inv: Record<string, number> = {}
  pool.forEach(v => { inv[v.vehicle_type] = (inv[v.vehicle_type] ?? 0) + v.quantity })

  const rows: AllocRow[] = []
  const summary: SummaryRow[] = []

  // Sort dealers by target desc (higher target → more vehicles, allocate first)
  const sorted = [...targets].filter(t => t.target > 0).sort((a,b) => b.target - a.target)
  const totalTarget = sorted.reduce((s,t) => s + t.target, 0)
  const totalInv    = Object.values(inv).reduce((s,v) => s + v, 0)
  const scale       = totalInv < totalTarget ? totalInv / totalTarget : 1.0

  sorted.forEach(({ dealer, target }) => {
    const adjTarget = Math.round(target * scale)
    let remaining = adjTarget
    let allocated = 0

    // Allocate proportionally across vehicle types
    const vtypes = Object.entries(inv).filter(([,q]) => q > 0)
    const totalAvail = vtypes.reduce((s,[,q]) => s + q, 0)

    vtypes.forEach(([vtype, avail]) => {
      if (remaining <= 0 || avail <= 0) return
      const share = Math.min(Math.round(adjTarget * avail / totalAvail), avail, remaining)
      if (share <= 0) return

      inv[vtype] -= share
      remaining  -= share
      allocated  += share

      // Parse vehicle_type back to parts (format: "Model / Version / Color")
      const parts = vtype.split(' / ')
      rows.push({ dealer, model: parts[0]??'', version: parts[1]??'', color: parts[2]??'', quantity: share })
    })

    // Fill remaining from any available stock
    if (remaining > 0) {
      const leftover = Object.entries(inv).filter(([,q]) => q > 0)
      for (const [vtype, avail] of leftover) {
        if (remaining <= 0) break
        const take = Math.min(remaining, avail)
        inv[vtype] -= take
        remaining  -= take
        allocated  += take
        const parts = vtype.split(' / ')
        rows.push({ dealer, model: parts[0]??'', version: parts[1]??'', color: parts[2]??'', quantity: take })
      }
    }

    const fill = target > 0 ? Math.round(allocated / target * 1000) / 10 : 0
    summary.push({ dealer, target, allocated, gap: allocated - target, fill_rate: fill })
  })

  return { rows, summary }
}

// ─── Step indicator ───────────────────────────────────────────────────────────
function Steps({ active }: { active: number }) {
  const steps = ['Envanter Yükle', 'Bayi Hedefleri', 'Dağıtımı Hesapla', 'Sonuçlar']
  return (
    <div className="flex items-center gap-0 mb-8">
      {steps.map((s, i) => {
        const done    = i < active
        const current = i === active
        return (
          <div key={s} className="flex items-center">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              current ? 'bg-blue-600 text-white' : done ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'
            }`}>
              {done ? <CheckCircle size={14} /> : <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs leading-none border-current">{i+1}</span>}
              {s}
            </div>
            {i < steps.length - 1 && <ChevronRight size={16} className="text-slate-300 mx-1" />}
          </div>
        )
      })}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Dagitim() {
  const [step, setStep]           = useState(0)
  const [month, setMonth]         = useState('Ocak')
  const [fileName, setFileName]   = useState('')
  const [parseError, setError]    = useState('')
  const [inventory, setInventory] = useState<VehicleRow[]>([])
  const [dealers, setDealers]     = useState<Dealer[]>([])
  const [targets, setTargets]     = useState<Record<string, number>>({})
  const [allocRows, setAllocRows] = useState<AllocRow[]>([])
  const [summary, setSummary]     = useState<SummaryRow[]>([])
  const [resultTab, setResultTab] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)

  // Load dealer list from JSON
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/dealers.json`)
      .then(r => r.json())
      .then((d: { name: string; active: boolean }[]) => setDealers(d.filter(x => x.active)))
  }, [])

  // Init targets when dealers load
  useEffect(() => {
    if (dealers.length && Object.keys(targets).length === 0) {
      const t: Record<string, number> = {}
      dealers.forEach(d => { t[d.name] = 0 })
      setTargets(t)
    }
  }, [dealers])

  // ── Excel parse ──────────────────────────────────────────────────────────────
  function handleFile(file: File) {
    setError('')
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data  = new Uint8Array(e.target!.result as ArrayBuffer)
        const wb    = XLSX.read(data, { type: 'array' })
        const ws    = wb.Sheets[wb.SheetNames[0]]
        const rows  = XLSX.utils.sheet_to_json<Record<string, string>>(ws, { defval: '' })

        // Normalize headers
        const norm = rows.map(r => {
          const out: Record<string,string> = {}
          Object.entries(r).forEach(([k,v]) => { out[k.trim()] = String(v).trim() })
          return out
        })

        // Detect month variants
        const monthVariants = MONTH_EN[month] ?? [month]

        // Filter
        const pool = norm.filter(r =>
          r['Dealer Code Processing'] === 'CENT-STOCK' &&
          r['Dispatchable'] === 'Y' &&
          monthVariants.some(mv => r['Month Number'] === mv || r['Month Number']?.toLowerCase() === mv.toLowerCase())
        )

        if (pool.length === 0) {
          // Show what Month Number values exist
          const found = [...new Set(norm.map(r => r['Month Number']))].filter(Boolean).slice(0, 10).join(', ')
          setError(`Filtre sonucu boş. Dosyada 'CENT-STOCK' + 'Dispatchable=Y' + ay='${month}' olan satır bulunamadı.\nDosyadaki Month Number değerleri: ${found || '(bulunamadı)'}`)
          return
        }

        // Aggregate by vehicle_type
        const agg: Record<string, VehicleRow> = {}
        pool.forEach(r => {
          const model   = r['Model Description'] ?? ''
          const version = r['Vehicle Version']   ?? ''
          const color   = r['Exterior Color']    ?? ''
          const vtype   = `${model} / ${version} / ${color}`
          if (!agg[vtype]) agg[vtype] = { model, version, color, vehicle_type: vtype, quantity: 0 }
          agg[vtype].quantity++
        })

        const result = Object.values(agg).sort((a,b) => b.quantity - a.quantity)
        setInventory(result)
        setFileName(file.name)
        setStep(1)
      } catch (err) {
        setError(`Dosya okunamadı: ${err}`)
      }
    }
    reader.readAsArrayBuffer(file)
  }

  const totalTarget    = Object.values(targets).reduce((s, v) => s + v, 0)
  const totalInventory = inventory.reduce((s, v) => s + v.quantity, 0)
  const overSupply     = totalTarget > totalInventory

  function runAndNext() {
    const tArr: Target[] = Object.entries(targets).map(([dealer, target]) => ({ dealer, target }))
    const { rows, summary: sum } = runAllocation(inventory, tArr)
    setAllocRows(rows)
    setSummary(sum.sort((a,b) => numSort(a.dealer, b.dealer)))
    setStep(3)
  }

  function reset() {
    setStep(0); setInventory([]); setFileName(''); setError('')
    const t: Record<string,number> = {}; dealers.forEach(d => { t[d.name] = 0 }); setTargets(t)
    setAllocRows([]); setSummary([]); setResultTab(0)
    if (fileRef.current) fileRef.current.value = ''
  }

  // ─── STEP 0: Upload ──────────────────────────────────────────────────────────
  const StepUpload = (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-2">Dağıtım Ayı</label>
          <select value={month} onChange={e => setMonth(e.target.value)}
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white w-48">
            {MONTHS.map(m => <option key={m}>{m}</option>)}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700 block mb-2">Envanter Dosyası</label>
          <p className="text-xs text-slate-500 mb-3">
            Excel (.xlsx) veya CSV dosyası. Gerekli sütunlar: <code className="bg-slate-100 px-1 rounded">Dealer Code Processing</code>, <code className="bg-slate-100 px-1 rounded">Dispatchable</code>, <code className="bg-slate-100 px-1 rounded">Month Number</code>, <code className="bg-slate-100 px-1 rounded">Model Description</code>, <code className="bg-slate-100 px-1 rounded">Vehicle Version</code>, <code className="bg-slate-100 px-1 rounded">Exterior Color</code>
          </p>
          <label className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-slate-300 rounded-xl p-10 cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
            <Upload size={28} className="text-slate-400" />
            <span className="text-sm text-slate-500">Dosyayı sürükleyin veya seçin</span>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </label>
        </div>

        {parseError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 whitespace-pre-wrap">
            {parseError}
          </div>
        )}
      </div>
    </div>
  )

  // ─── STEP 1: Inventory review + go to targets ─────────────────────────────
  const uniqueModels   = [...new Set(inventory.map(v => v.model))].length
  const uniqueVersions = [...new Set(inventory.map(v => v.version))].length
  const uniqueColors   = [...new Set(inventory.map(v => v.color))].length

  const StepInventory = (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-green-800">{fileName}</p>
          <p className="text-xs text-green-600 mt-0.5">{month} · CENT-STOCK · Dispatchable=Y</p>
        </div>
        <button onClick={reset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-500 transition-colors">
          <RotateCcw size={13} /> Baştan Başla
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Toplam Araç', totalInventory, 'text-blue-600'],
          ['Farklı Tip', inventory.length, 'text-slate-900'],
          ['Model Sayısı', uniqueModels, 'text-slate-900'],
          ['Renk Sayısı', uniqueColors, 'text-slate-900'],
        ].map(([lbl, val, cls]) => (
          <div key={lbl as string} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">{lbl}</p>
            <p className={`text-2xl font-bold ${cls}`}>{val}</p>
          </div>
        ))}
      </div>

      {/* Inventory table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-slate-700">Araç Havuzu — {inventory.length} tip, {totalInventory} araç</h3>
          <span className="text-xs text-slate-400">{uniqueVersions} farklı versiyon</span>
        </div>
        <div className="overflow-auto max-h-64">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
              <tr>
                {['Model','Versiyon','Renk','Adet'].map(h => (
                  <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${h==='Adet'?'text-right':'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inventory.map((v, i) => (
                <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-900">{v.model}</td>
                  <td className="px-4 py-2 text-slate-600">{v.version}</td>
                  <td className="px-4 py-2 text-slate-600">{v.color}</td>
                  <td className="px-4 py-2 text-right font-semibold text-blue-600">{v.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <button onClick={() => setStep(2)}
        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
        Bayi Hedeflerine Geç <ChevronRight size={16} />
      </button>
    </div>
  )

  // ─── STEP 2: Dealer targets ───────────────────────────────────────────────
  const StepTargets = (
    <div className="space-y-6">
      {/* Live counter */}
      <div className={`rounded-xl border p-4 ${overSupply ? 'bg-red-50 border-red-200' : totalTarget > 0 ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className={`text-3xl font-bold ${overSupply ? 'text-red-600' : 'text-blue-600'}`}>{totalTarget}</span>
            <span className="text-slate-500 text-sm ml-2">/ {totalInventory} araç</span>
          </div>
          <div className={`text-xs font-semibold px-3 py-1 rounded-full ${overSupply ? 'bg-red-100 text-red-700' : totalTarget > 0 ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
            {overSupply ? '⚠ Arz aşıldı!' : totalTarget > 0 ? '✓ Arz yeterli' : 'Henüz girilmedi'}
          </div>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div className="h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, totalInventory > 0 ? totalTarget/totalInventory*100 : 0)}%`, background: overSupply ? '#ef4444' : '#3b82f6' }} />
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>Toplam Talep</span>
          <span>Kalan: {Math.max(0, totalInventory - totalTarget)} araç</span>
        </div>
      </div>

      {/* Reset button */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-600 font-medium">Bayi başına aylık hedef girin:</p>
        <button onClick={() => { const t: Record<string,number> = {}; dealers.forEach(d => { t[d.name] = 0 }); setTargets(t) }}
          className="text-xs text-slate-400 hover:text-red-500 flex items-center gap-1 transition-colors">
          <RotateCcw size={12} /> Tümünü Sıfırla
        </button>
      </div>

      {/* Dealer grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {[...dealers].sort((a,b) => numSort(a.name, b.name)).map(d => {
          const val = targets[d.name] ?? 0
          return (
            <div key={d.name} className={`bg-white rounded-xl border p-3 transition-colors ${val > 0 ? 'border-blue-300 bg-blue-50' : 'border-slate-200'}`}>
              <p className="text-xs font-semibold text-slate-700 mb-2">{d.name}</p>
              <input
                type="number"
                min={0}
                max={500}
                value={val === 0 ? '' : val}
                placeholder="0"
                onChange={e => setTargets(prev => ({ ...prev, [d.name]: Math.max(0, parseInt(e.target.value) || 0) }))}
                className="w-full text-center text-lg font-bold border border-slate-200 rounded-lg py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="text-xs text-slate-400 text-center mt-1">araç/ay</p>
            </div>
          )
        })}
      </div>

      <div className="flex gap-3">
        <button onClick={() => setStep(1)} className="px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
          ← Geri
        </button>
        <button
          disabled={totalTarget === 0 || overSupply}
          onClick={() => setStep(3)}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          Dağıtımı Hesapla <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )

  // ─── STEP 3: Results ──────────────────────────────────────────────────────
  const totalAllocated = summary.reduce((s,r) => s + r.allocated, 0)
  const fillRate       = totalInventory > 0 ? totalAllocated / totalInventory * 100 : 0

  // Model breakdown
  const modelBreakdown = (() => {
    const agg: Record<string, number> = {}
    allocRows.forEach(r => { agg[r.model] = (agg[r.model] ?? 0) + r.quantity })
    return Object.entries(agg).map(([model, qty]) => ({ model, qty })).sort((a,b) => b.qty - a.qty)
  })()

  // Stacked bar: dealer × model
  const dealerOrder = summary.map(s => s.dealer)
  const allModels   = [...new Set(allocRows.map(r => r.model))].sort()
  const stackedData = dealerOrder.map(dealer => {
    const row: Record<string,unknown> = { dealer }
    allModels.forEach(m => {
      row[m] = allocRows.filter(r => r.dealer === dealer && r.model === m).reduce((s,r) => s+r.quantity, 0)
    })
    return row
  })

  const resultTabs = ['Dağıtım Tablosu', 'Bayi Özeti', 'Model Dağılımı']

  const StepResults = (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Toplam Envanter',  totalInventory.toLocaleString('tr'),  'text-slate-900'],
          ['Toplam Atanan',    totalAllocated.toLocaleString('tr'),  'text-blue-600'],
          ['Doluluk Oranı',    `%${fillRate.toFixed(1)}`,            fillRate >= 85 ? 'text-green-600' : 'text-amber-600'],
          ['Aktif Bayi',       summary.length.toString(),            'text-slate-900'],
        ].map(([lbl, val, cls]) => (
          <div key={lbl} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">{lbl}</p>
            <p className={`text-2xl font-bold ${cls}`}>{val}</p>
          </div>
        ))}
      </div>

      {/* Result tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
        {resultTabs.map((t, i) => (
          <button key={t} onClick={() => setResultTab(i)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${resultTab===i ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Dağıtım Tablosu */}
      {resultTab === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-auto max-h-[560px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
                <tr>
                  {['Bayi','Model','Versiyon','Renk','Adet'].map(h => (
                    <th key={h} className={`px-4 py-2.5 font-medium text-slate-500 text-xs ${h==='Adet'?'text-right':'text-left'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...allocRows].sort((a,b) => numSort(a.dealer, b.dealer) || a.model.localeCompare(b.model)).map((r, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-900 whitespace-nowrap">{r.dealer}</td>
                    <td className="px-4 py-2 text-slate-700">{r.model}</td>
                    <td className="px-4 py-2 text-slate-600">{r.version}</td>
                    <td className="px-4 py-2 text-slate-600">{r.color}</td>
                    <td className="px-4 py-2 text-right font-semibold text-blue-600">{r.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bayi Özeti */}
      {resultTab === 1 && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
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
                  {summary.map(r => (
                    <tr key={r.dealer} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-900">{r.dealer}</td>
                      <td className="px-4 py-2.5 text-right text-slate-600">{r.target}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-blue-600">{r.allocated}</td>
                      <td className={`px-4 py-2.5 text-right font-semibold ${r.gap >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.gap >= 0 ? '+' : ''}{r.gap}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${r.fill_rate >= 85 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          %{r.fill_rate.toFixed(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Hedef vs Atanan</h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={summary} margin={{ left: 0, right: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="target"    name="Hedef"  fill="#cbd5e1" radius={[4,4,0,0]} />
                <Bar dataKey="allocated" name="Atanan" radius={[4,4,0,0]}>
                  {summary.map((r,i) => <Cell key={i} fill={r.fill_rate >= 85 ? '#22c55e' : '#f59e0b'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Model Dağılımı */}
      {resultTab === 2 && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Bayi × Model (Stacked)</h3>
            <ResponsiveContainer width="100%" height={380}>
              <BarChart data={stackedData} margin={{ left: 0, right: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dealer" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {allModels.map((m,i) => (
                  <Bar key={m} dataKey={m} stackId="a" fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Model Bazında Toplam</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={modelBreakdown} layout="vertical" margin={{ left: 20, right: 50 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="model" tick={{ fontSize: 12 }} width={40} />
                <Tooltip />
                <Bar dataKey="qty" name="Atanan" radius={[0,4,4,0]}>
                  {modelBreakdown.map((_,i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  <LabelList dataKey="qty" position="right" style={{ fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={() => setStep(2)} className="px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
          ← Hedefleri Düzenle
        </button>
        <button onClick={reset} className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
          <RotateCcw size={14} /> Yeni Dağıtım
        </button>
      </div>
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Dağıtım Sistemi</h1>
        <p className="text-slate-500 text-sm mt-1">Envanter yükle → hedefleri gir → optimal dağıtımı hesapla</p>
      </div>

      <Steps active={step === 3 ? 3 : step} />

      {step === 0 && StepUpload}
      {step === 1 && StepInventory}
      {step === 2 && StepTargets}
      {step === 3 && StepResults}
    </div>
  )
}
