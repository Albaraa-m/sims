import { BrowserRouter, NavLink, Route, Routes } from 'react-router'

import DashboardPage from '@/pages/DashboardPage'
import NewSwarmPage from '@/pages/NewSwarmPage'
import ResultsPage from '@/pages/ResultsPage'
import RunPage from '@/pages/RunPage'
import SwarmPage from '@/pages/SwarmPage'
import SwarmsPage from '@/pages/SwarmsPage'
import TestPage from '@/pages/TestPage'
import TestsPage from '@/pages/TestsPage'

export default function App() {
  return (
    <BrowserRouter>
      <nav className="mx-auto flex max-w-5xl gap-4 px-6 pt-6 text-sm">
        {[
          { to: '/', label: 'Tests' },
          { to: '/swarms', label: 'Swarms' },
          { to: '/results', label: 'Results' },
          { to: '/dashboard', label: 'Dashboard' },
        ].map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) => (isActive ? 'font-medium' : 'text-muted-foreground hover:text-foreground')}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Routes>
          <Route path="/" element={<TestsPage />} />
          <Route path="/tests/:testId" element={<TestPage />} />
          <Route path="/runs/:runId" element={<RunPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/swarms" element={<SwarmsPage />} />
          <Route path="/swarms/new" element={<NewSwarmPage />} />
          <Route path="/swarms/:swarmId" element={<SwarmPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
