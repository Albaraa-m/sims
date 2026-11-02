import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { listRunsOfAllTests } from '@/api'
import AgentQualityTab from '@/components/AgentQualityTab'
import Filter from '@/components/Filter'
import SystemHealthTab from '@/components/SystemHealthTab'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { listJudgesNewestFirst } from '@/dashboard'
import type { RunRow } from '@/types'

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    listRunsOfAllTests({}).then(
      (loadedRuns) => {
        setRuns(loadedRuns)
        setLoadedAt(Date.now())
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [])

  const setParam = (name: string, value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next, { replace: true })
  }
  const tab = searchParams.get('tab') ?? 'quality'
  const judges = runs ? listJudgesNewestFirst(runs) : []
  const judge = searchParams.get('judge') ?? judges[0] ?? ''

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
            {judges.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                Graded by
                <Filter
                  label="Judge"
                  value={judge}
                  options={judges.map((name) => ({ value: name, label: name }))}
                  onChange={(value) => setParam('judge', value)}
                />
              </div>
            )}
            <AgentQualityTab runs={runs} judge={judge} />
          </TabsContent>
          <TabsContent value="health" className="space-y-6 pt-4">
            <SystemHealthTab runs={runs} now={loadedAt} />
          </TabsContent>
        </Tabs>
      )}
    </section>
  )
}
