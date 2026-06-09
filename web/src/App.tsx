import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import GecmisAnaliz from './pages/GecmisAnaliz'
import Mevsimsellik from './pages/Mevsimsellik'
import BayiHarita from './pages/BayiHarita'
import Dagitim from './pages/Dagitim'
import Tahmin from './pages/Tahmin'
import PazarHedefleri from './pages/PazarHedefleri'

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-56 flex-1 p-6 min-h-screen">
        <Routes>
          <Route path="/" element={<Navigate to="/gecmis-analiz" replace />} />
          <Route path="/gecmis-analiz"   element={<GecmisAnaliz />} />
          <Route path="/mevsimsellik"    element={<Mevsimsellik />} />
          <Route path="/bayi-harita"     element={<BayiHarita />} />
          <Route path="/dagitim"         element={<Dagitim />} />
          <Route path="/tahmin"          element={<Tahmin />} />
          <Route path="/pazar-hedefleri" element={<PazarHedefleri />} />
        </Routes>
      </main>
    </div>
  )
}
