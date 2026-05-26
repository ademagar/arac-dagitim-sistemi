import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Araç Dağıtım Sistemi',
  description: 'Otomotiv bayi araç dağıtım karar destek sistemi',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className={inter.className}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="ml-56 flex-1 p-6 min-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
