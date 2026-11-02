import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { listRunsOfAllTests } from '@/api'
import ScopeSelect from '@/components/ScopeSelect'
import AgentQualitySection from '@/components/AgentQualitySection'
import SystemHealthSection from '@/components/SystemHealthSection'
import { REGRESSION_SCOPE } from '@/scopes'
import type { RunRow } from '@/types'

const POLL_INTERVAL_MS = 3000

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  // Every run, for system health; and the scope's runs, for agent quality.
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [scopedRuns, setScopedRuns] = useState<RunRow[] | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadRuns = useCallback(() => {
    listRunsOfAllTests({}).then(
      (loadedRuns) => {
        setRuns(loadedRuns)
        setLoadedAt(Date.now())
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [])

  // System health is watched live during a run; agent quality changes only after runs.
  useEffect(() => {
    loadRuns()
    const interval = setInterval(loadRuns, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [loadRuns])

  const scope = searchParams.get('scope') ?? REGRESSION_SCOPE
  useEffect(() => {
    listRunsOfAllTests({ scope }).then(setScopedRuns, (error: Error) => setLoadError(error.message))
  }, [scope])

  const setScope = (value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('scope', value)
    else next.delete('scope')
    setSearchParams(next, { replace: true })
  }

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      {loadError && <p className="text-sm text-destructive">Couldn't load simulations: {loadError}</p>}
      <section className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">Agent quality</h2>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            Tests
            <ScopeSelect value={scope} onChange={setScope} />
          </div>
        </div>
        {scopedRuns && <AgentQualitySection runs={scopedRuns} scope={scope} />}
      </section>
      <section className="space-y-6 border-t pt-6">
        <h2 className="text-lg font-semibold">System health</h2>
        {runs && <SystemHealthSection runs={runs} now={loadedAt} />}
      </section>
    </section>
  )
}
