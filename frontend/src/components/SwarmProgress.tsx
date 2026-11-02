import { Link } from 'react-router'

import { OUTCOME_LABEL, RUN_STATUS_LABEL } from '@/runs'
import type { Outcome, RunRow, RunStatus, SwarmTest } from '@/types'

const STATUSES: RunStatus[] = ['queued', 'running', 'done', 'failed', 'cancelled']
const OUTCOMES: Outcome[] = ['pass', 'fail', 'inconclusive']

function cellLabel(run: RunRow): string {
  if (run.status === 'done' && run.outcome) return OUTCOME_LABEL[run.outcome]
  return RUN_STATUS_LABEL[run.status]
}

type SwarmProgressProps = {
  tests: SwarmTest[]
  runs: RunRow[]
}

// Counts that always add up to the runs requested, and a grid of each test by version.
export default function SwarmProgress({ tests, runs }: SwarmProgressProps) {
  if (runs.length === 0) return null
  const agentVersions = [...new Set(runs.map((run) => run.agent_version))].sort()
  const count = (match: (run: RunRow) => boolean) => runs.filter(match).length
  const retried = count((run) => run.attempts.some((entry) => entry.status !== 'completed'))

  return (
    <div className="space-y-4">
      <div className="space-y-1 rounded-lg border p-4 text-sm">
        <p>
          <span className="font-medium">{runs.length} runs</span>
          {STATUSES.map((status) => (
            <span key={status} className="text-muted-foreground">
              {' '}
              · {RUN_STATUS_LABEL[status]} {count((run) => run.status === status)}
            </span>
          ))}
        </p>
        <p className="text-muted-foreground">
          Outcomes
          {OUTCOMES.map((outcome) => (
            <span key={outcome}>
              {' '}
              · {OUTCOME_LABEL[outcome]} {count((run) => run.outcome === outcome)}
            </span>
          ))}
          {retried > 0 && <> · Retried {retried}</>}
        </p>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2 font-medium">Test</th>
            {agentVersions.map((version) => (
              <th key={version} className="py-2 font-medium">
                Agent {version}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tests.map((test) => (
            <tr key={test.id} className="border-b">
              <td className="py-2 pr-4">{test.name}</td>
              {agentVersions.map((version) => {
                const cellRuns = runs.filter((run) => run.test_id === test.id && run.agent_version === version)
                return (
                  <td key={version} className="py-2 pr-4">
                    {cellRuns.length === 0 && <span className="text-muted-foreground">–</span>}
                    {cellRuns.map((run) => (
                      <Link key={run.id} to={`/runs/${run.id}`} className="mr-3 underline-offset-4 hover:underline">
                        {cellLabel(run)}
                        {run.attempts.length > 1 && (
                          <span className="text-muted-foreground"> ×{run.attempts.length}</span>
                        )}
                      </Link>
                    ))}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
