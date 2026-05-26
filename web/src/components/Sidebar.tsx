'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart2, Calendar, Map, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { href: '/gecmis-analiz', label: 'Geçmiş Analiz',     icon: BarChart2 },
  { href: '/mevsimsellik',  label: 'Mevsimsellik',       icon: Calendar  },
  { href: '/bayi-harita',   label: 'Bayi Harita',        icon: Map       },
]

export default function Sidebar() {
  const path = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-slate-900 flex flex-col z-10">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <TrendingUp className="text-blue-400" size={22} />
          <div>
            <p className="text-white font-bold text-sm leading-tight">Araç Dağıtım</p>
            <p className="text-slate-400 text-xs">Sistemi</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white',
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-700">
        <p className="text-slate-500 text-xs">2026 · Demo Modu</p>
      </div>
    </aside>
  )
}
