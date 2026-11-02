import { Link } from 'react-router'

import OutcomeBadge from '@/components/OutcomeBadge'
import { SwarmRunStatusLabel } from '@/components/SwarmRunList'
import { Badge } from '@/components/ui/badge'
import { OUTCOME_BADGE_VARIANT, OUTCOME_LABEL, RUN_STATUS_BADGE_VARIANT, RUN_STATUS_LABEL } from '@/runs'
import type { Outcome, RunRow, RunStatus, SwarmRunSummary, SwarmTest } from '@/types'

const OUTCOMES: Outcome[] = ['pass', 'fail', 'inconclusive']
const IN_PROGRESS: RunStatus[] = ['running', 'queued']
const STOPPED: RunStatus[] = ['failed', 'cancelled']

// A call's pill: its grade once done, otherwise where it is in the queue.
function CallPill({ run, now }: { run: RunRow; now: number }) {
  if (run.status === 'done') return <OutcomeBadge run={run} now={now} />
  return <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
}

type SwarmRunDetailProps = {
  summary: SwarmRunSummary
  tests: SwarmTest[]
  runs: RunRow[]
  now: number
}

export default function SwarmRunDetail({ summary, tests, runs, now }: SwarmRunDetailProps) {
  const settled = runs.filter((run) => !IN_PROGRESS.includes(run.status)).length
  const agentVersions = [...new Set(runs.map((run) => run.agent_version))].sort()
  const testsInRun = tests.filter((test) => runs.some((run) => run.test_id === test.id))

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="space-y-3">
        <div className="flex items-center gap-3 text-sm">
          <h3 className="text-base font-semibold">
            {summary.number > 0 ? `Run #${summary.number}` : 'Earlier runs'}
          </h3>
          <SwarmRunStatusLabel status={summary.status} />
          <span className="ml-auto tabular-nums text-muted-foreground">
            {settled} of {runs.length} done
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${runs.length ? (settled / runs.length) * 100 : 0}%` }}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {OUTCOMES.map((outcome) => (
            <Badge key={outcome} variant={OUTCOME_BADGE_VARIANT[outcome]}>
              {summary.outcome_counts[outcome] ?? 0} {OUTCOME_LABEL[outcome]}
            </Badge>
          ))}
          {[...IN_PROGRESS, ...STOPPED]
            .filter((status) => summary.status_counts[status])
            .map((status) => (
              <Badge key={status} variant={RUN_STATUS_BADGE_VARIANT[status]}>
                {summary.status_counts[status]} {RUN_STATUS_LABEL[status]}
              </Badge>
            ))}
        </div>
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
          {testsInRun.map((test) => (
            <tr key={test.id} className="border-b last:border-0">
              <td className="py-2 pr-4">{test.name}</td>
              {agentVersions.map((version) => {
                const cellRuns = runs.filter((run) => run.test_id === test.id && run.agent_version === version)
                return (
                  <td key={version} className="py-2 pr-4">
                    <span className="flex flex-wrap items-center gap-1.5">
                      {cellRuns.length === 0 && <span className="text-muted-foreground">—</span>}
                      {cellRuns.map((run) => (
                        <Link key={run.id} to={`/simulations/${run.id}`} className="inline-flex items-center gap-1 hover:opacity-80">
                          <CallPill run={run} now={now} />
                          {run.attempts.length > 1 && (
                            <span className="text-xs text-muted-foreground">×{run.attempts.length}</span>
                          )}
                        </Link>
                      ))}
                    </span>
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
