import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { cancelSwarmRuns, listRunsOfSwarm, readSwarm, startSwarmRuns } from '@/api'
import RunControls from '@/components/RunControls'
import SwarmProgress from '@/components/SwarmProgress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { isActive, startedAtFormat, TEST_STATUS_BADGE_VARIANT, TEST_STATUS_LABEL } from '@/runs'
import type { RunRow, SwarmDetail } from '@/types'

const POLL_INTERVAL_MS = 3000

export default function SwarmPage() {
  const { swarmId } = useParams()
  const [swarm, setSwarm] = useState<SwarmDetail | null>(null)
  const [runs, setRuns] = useState<RunRow[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)

  useEffect(() => {
    if (swarmId) readSwarm(swarmId).then(setSwarm, (error: Error) => setLoadError(error.message))
  }, [swarmId])

  const loadRuns = useCallback(() => {
    if (swarmId) listRunsOfSwarm(swarmId).then(setRuns, (error: Error) => setLoadError(error.message))
  }, [swarmId])

  useEffect(loadRuns, [loadRuns])

  const hasActiveRuns = runs.some(isActive)
  useEffect(() => {
    if (!hasActiveRuns) return
    const interval = setInterval(loadRuns, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [hasActiveRuns, loadRuns])

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
        <div className="flex items-center gap-3">
          <h2 className="text-base font-semibold">Runs</h2>
          {hasActiveRuns && (
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              disabled={isCancelling}
              onClick={() => {
                setIsCancelling(true)
                cancelSwarmRuns(swarm.id)
                  .then(loadRuns, (error: Error) => setLoadError(error.message))
                  .finally(() => setIsCancelling(false))
              }}
            >
              {isCancelling ? 'Cancelling…' : 'Cancel'}
            </Button>
          )}
        </div>
        <RunControls
          startRuns={(agentVersions, runsPerTest) => startSwarmRuns(swarm.id, agentVersions, runsPerTest)}
          onStarted={loadRuns}
          testCount={swarm.tests.length}
        />
        <SwarmProgress tests={swarm.tests} runs={runs} />
      </div>

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
              {test.version > 1 && <span className="text-muted-foreground">v{test.version}</span>}
            </div>
            <p className="text-muted-foreground">
              <span className="text-foreground">Policy:</span> {test.spec.policy_under_test}
            </p>
            <p className="text-muted-foreground">
              <span className="text-foreground">Caller:</span> {test.spec.behavior}
            </p>
          </Link>
        ))}
      </div>
    </section>
  )
}
