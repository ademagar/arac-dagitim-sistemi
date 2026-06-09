import { NavLink } from 'react-router-dom'
import { BarChart2, Calendar, Map, TrendingUp, Truck, LineChart, Target, BookOpen, FileText } from 'lucide-react'

const NAV = [
  { to: '/gecmis-analiz',    label: 'Geçmiş Analiz',    icon: BarChart2  },
  { to: '/mevsimsellik',     label: 'Mevsimsellik',      icon: Calendar   },
  { to: '/bayi-harita',      label: 'Bayi Harita',       icon: Map        },
  { to: '/dagitim',          label: 'Dağıtım',           icon: Truck      },
  { to: '/tahmin',           label: 'Tahmin & Plan',     icon: LineChart  },
  { to: '/pazar-hedefleri',  label: 'Pazar Hedefleri',  icon: Target     },
  { to: '/aylik-bayi-hedef', label: 'Aylık Bayi Hedef', icon: BookOpen   },
  { to: '/ozet',             label: 'Sistem Özeti',      icon: FileText   },
]

export default function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-slate-900 flex flex-col z-10">
      <div className="px-5 py-6 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <TrendingUp className="text-blue-400" size={22} />
          <div>
            <p className="text-white font-bold text-sm leading-tight">Araç Dağıtım</p>
            <p className="text-slate-400 text-xs">Sistemi</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-slate-700">
        <p className="text-slate-500 text-xs">2026 · Demo Modu</p>
      </div>
    </aside>
  )
}
