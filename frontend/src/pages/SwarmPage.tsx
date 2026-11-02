import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { readSwarm } from '@/api'
import { Badge } from '@/components/ui/badge'
import { startedAtFormat, TEST_STATUS_LABEL } from '@/runs'
import { groupByPolicy } from '@/swarms'
import type { SwarmDetail } from '@/types'

export default function SwarmPage() {
  const { swarmId } = useParams()
  const [swarm, setSwarm] = useState<SwarmDetail | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (swarmId) readSwarm(swarmId).then(setSwarm, (error: Error) => setLoadError(error.message))
  }, [swarmId])

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the swarm: {loadError}</p>
  if (!swarm) return null

  const groups = groupByPolicy(swarm.policies, swarm.tests, (test) => test.spec.policy_under_test)
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/swarms" className="text-sm text-muted-foreground hover:text-foreground">
          Swarms
        </Link>
        <h1 className="text-xl font-semibold">{swarm.name}</h1>
        <p className="text-sm text-muted-foreground">
          Agent {swarm.agent_version} · {swarm.test_count} tests · {swarm.policies.length} policies · Created{' '}
          {startedAtFormat.format(new Date(swarm.created_at))}
        </p>
      </div>

      {groups.map(({ policy, items }) => (
        <div key={policy} className="space-y-2">
          <h2 className="text-base font-semibold">
            {policy}{' '}
            <span className="font-normal text-muted-foreground">
              · {items.length} {items.length === 1 ? 'test' : 'tests'}
            </span>
          </h2>
          {items.length === 0 && <p className="text-sm text-muted-foreground">Not covered by any test.</p>}
          {items.map((test) => (
            <Link
              key={test.id}
              to={`/tests/${test.id}`}
              className="block space-y-1 rounded-lg border p-3 text-sm hover:bg-muted/50"
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">{test.name}</span>
                <Badge variant={test.status === 'ready' ? 'default' : 'secondary'}>
                  {TEST_STATUS_LABEL[test.status]}
                </Badge>
                {test.version > 1 && <span className="text-muted-foreground">v{test.version}</span>}
              </div>
              <p className="text-muted-foreground">{test.spec.behavior}</p>
            </Link>
          ))}
        </div>
      ))}
    </section>
  )
}
