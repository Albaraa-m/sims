import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useParams } from 'react-router'

import DashboardPage from '@/pages/DashboardPage'
import NewSwarmPage from '@/pages/NewSwarmPage'
import ResultsPage from '@/pages/ResultsPage'
import RunPage from '@/pages/RunPage'
import SwarmPage from '@/pages/SwarmPage'
import SwarmsPage from '@/pages/SwarmsPage'
import TestPage from '@/pages/TestPage'
import TestsPage from '@/pages/TestsPage'

// Old links (/runs/:id, /results) still work after the rename to simulations.
function RedirectOldSimulationLink() {
  const { runId } = useParams()
  return <Navigate to={`/simulations/${runId}`} replace />
}

function RedirectOldResultsLink() {
  return <Navigate to={`/simulations${useLocation().search}`} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <header className="border-b bg-card">
        <nav className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-6 text-sm">
          {/* The brand, set apart from the tabs so it doesn't read as one. */}
          <Link to="/" className="flex items-center gap-2 pr-6 text-base font-semibold tracking-tight">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
              S
            </span>
            Sims
          </Link>
          <span className="-ml-6 h-6 w-px bg-border" />
          {[
            { to: '/', label: 'Regression tests' },
            { to: '/swarms', label: 'Swarms' },
            { to: '/simulations', label: 'Simulations' },
            { to: '/dashboard', label: 'Dashboard' },
          ].map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex h-full items-center border-b-2 ${
                  isActive
                    ? 'border-primary font-medium text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Routes>
          <Route path="/" element={<TestsPage />} />
          <Route path="/tests/:testId" element={<TestPage />} />
          <Route path="/simulations" element={<ResultsPage />} />
          <Route path="/simulations/:runId" element={<RunPage />} />
          <Route path="/runs/:runId" element={<RedirectOldSimulationLink />} />
          <Route path="/results" element={<RedirectOldResultsLink />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/swarms" element={<SwarmsPage />} />
          <Route path="/swarms/new" element={<NewSwarmPage />} />
          <Route path="/swarms/:swarmId" element={<SwarmPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
