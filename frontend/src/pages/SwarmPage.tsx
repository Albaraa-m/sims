import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { cancelSwarmRun, listRunsOfSwarmRun, listSwarmRuns, readSwarm, startSwarmRuns } from '@/api'
import RunControls from '@/components/RunControls'
import SwarmRunDetail from '@/components/SwarmRunDetail'
import SwarmRunList from '@/components/SwarmRunList'
import TestSpecSummary from '@/components/TestSpecSummary'
import { Badge } from '@/components/ui/badge'
import { startedAtFormat, TEST_STATUS_BADGE_VARIANT, TEST_STATUS_LABEL } from '@/runs'
import type { RunRow, SwarmDetail, SwarmRunSummary } from '@/types'

const POLL_INTERVAL_MS = 3000

export default function SwarmPage() {
  const { swarmId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [swarm, setSwarm] = useState<SwarmDetail | null>(null)
  const [summaries, setSummaries] = useState<SwarmRunSummary[]>([])
  const [runs, setRuns] = useState<RunRow[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)

  // The run shown below the list: the one in the URL, else the newest.
  const selectedId = searchParams.get('run') ?? summaries[0]?.id ?? null
  const selected = summaries.find((summary) => summary.id === selectedId) ?? null

  useEffect(() => {
    if (swarmId) readSwarm(swarmId).then(setSwarm, (error: Error) => setLoadError(error.message))
  }, [swarmId])

  const loadRuns = useCallback(() => {
    if (!swarmId) return
    listSwarmRuns(swarmId).then(setSummaries, (error: Error) => setLoadError(error.message))
    if (selectedId) {
      listRunsOfSwarmRun(swarmId, selectedId).then(
        (loadedRuns) => {
          setRuns(loadedRuns)
          setLoadedAt(Date.now())
        },
        (error: Error) => setLoadError(error.message),
      )
    }
  }, [swarmId, selectedId])

  useEffect(loadRuns, [loadRuns])

  const hasActiveRuns = summaries.some((summary) => summary.status === 'running' || summary.status === 'queued')
  useEffect(() => {
    if (!hasActiveRuns) return
    const interval = setInterval(loadRuns, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [hasActiveRuns, loadRuns])

  function selectRun(id: string) {
    setSearchParams({ run: id }, { replace: true })
  }

  function cancelRun(id: string) {
    if (!swarmId) return
    setCancellingId(id)
    cancelSwarmRun(swarmId, id)
      .then(loadRuns, (error: Error) => setLoadError(error.message))
      .finally(() => setCancellingId(null))
  }

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the swarm: {loadError}</p>
  if (!swarm) return null

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/swarms" className="text-sm text-muted-foreground hover:text-foreground">
          Swarms
        </Link>
        <h1 className="text-xl font-semibold">{swarm.name}</h1>
        <p className="text-sm text-muted-foreground">
          Agent {swarm.agent_version} · {swarm.test_count} tests, one per policy · Created{' '}
          {startedAtFormat.format(new Date(swarm.created_at))}
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Runs</h2>
          <RunControls
            startRuns={(agentVersions, runsPerTest) =>
              startSwarmRuns(swarm.id, agentVersions, runsPerTest).then((queued) => {
                if (queued.swarm_run_id) selectRun(queued.swarm_run_id)
              })
            }
            onStarted={loadRuns}
            testCount={swarm.tests.length}
          />
        </div>
        {summaries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not run yet. Pick agent versions and run the swarm.</p>
        ) : (
          <SwarmRunList
            summaries={summaries}
            selectedId={selectedId}
            onSelect={selectRun}
            onCancel={cancelRun}
            cancellingId={cancellingId}
          />
        )}
        {selected && <SwarmRunDetail summary={selected} tests={swarm.tests} runs={runs} now={loadedAt} />}
      </div>

      <h2 className="text-base font-semibold">Tests</h2>
      <div className="space-y-2">
        {swarm.tests.map((test) => (
          <Link
            key={test.id}
            to={`/tests/${test.id}`}
            className="block space-y-1 rounded-lg border p-3 text-sm hover:bg-muted/50"
          >
            <div className="flex items-center gap-2">
              <span className="font-medium">{test.name}</span>
              <Badge variant={TEST_STATUS_BADGE_VARIANT[test.status]}>
                {TEST_STATUS_LABEL[test.status]}
              </Badge>
              {test.promoted_from_swarm_id && <Badge variant="info">Promoted</Badge>}
              {test.version > 1 && <span className="text-muted-foreground">v{test.version}</span>}
            </div>
            <TestSpecSummary spec={test.spec} />
          </Link>
        ))}
      </div>
    </section>
  )
}
