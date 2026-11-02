import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { listRunsOfAllTests } from '@/api'
import ScopeSelect from '@/components/ScopeSelect'
import AgentQualityTab from '@/components/AgentQualityTab'
import SystemHealthTab from '@/components/SystemHealthTab'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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

  useEffect(loadRuns, [loadRuns])

  const scope = searchParams.get('scope') ?? REGRESSION_SCOPE
  useEffect(() => {
    listRunsOfAllTests({ scope }).then(setScopedRuns, (error: Error) => setLoadError(error.message))
  }, [scope])

  const setParam = (name: string, value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next, { replace: true })
  }
  const tab = searchParams.get('tab') ?? 'quality'

  // System health is watched live during a run; agent quality changes only after runs.
  useEffect(() => {
    if (tab !== 'health') return
    const interval = setInterval(loadRuns, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [tab, loadRuns])

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      {loadError && <p className="text-sm text-destructive">Couldn't load runs: {loadError}</p>}
      {runs && (
        <Tabs value={tab} onValueChange={(value) => setParam('tab', value)}>
          <TabsList>
            <TabsTrigger value="quality">Agent quality</TabsTrigger>
            <TabsTrigger value="health">System health</TabsTrigger>
          </TabsList>
          <TabsContent value="quality" className="space-y-6 pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              Tests
              <ScopeSelect value={scope} onChange={(value) => setParam('scope', value)} />
            </div>
            {scopedRuns && <AgentQualityTab runs={scopedRuns} scope={scope} />}
          </TabsContent>
          <TabsContent value="health" className="space-y-6 pt-4">
            <SystemHealthTab runs={runs} now={loadedAt} />
          </TabsContent>
        </Tabs>
      )}
    </section>
  )
}
