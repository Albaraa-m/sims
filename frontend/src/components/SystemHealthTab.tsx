import { Link } from 'react-router'

import LiveQueuePanel from '@/components/LiveQueuePanel'
import LoadOverTimeChart from '@/components/LoadOverTimeChart'
import RunHealthOverTimeChart from '@/components/RunHealthOverTimeChart'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { durationSeconds, judgeOfRun, median, resultsUrl } from '@/dashboard'
import { EXECUTION_FAILURE_KIND_LABEL, formatRunDuration, isActive, isAwaitingGrade } from '@/runs'
import type { ExecutionFailureKind, RunRow } from '@/types'

function Count({ label, value, to }: { label: string; value: number; to?: string }) {
  const content = (
    <>
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </>
  )
  return to ? (
    <Link to={to} className="rounded-lg border p-3 hover:bg-muted/50">
      {content}
    </Link>
  ) : (
    <div className="rounded-lg border p-3">{content}</div>
  )
}

function formatSeconds(seconds: number | null): string {
  if (seconds === null) return '—'
  const rounded = Math.round(seconds)
  return `${Math.floor(rounded / 60)}m ${String(rounded % 60).padStart(2, '0')}s`
}

export default function SystemHealthTab({ runs, now }: { runs: RunRow[]; now: number }) {
  // Each run lands in exactly one bucket, so the counts add up to the total.
  const inProgressRuns = runs.filter((run) => isActive(run) || isAwaitingGrade(run, now))
  const executionFailures = runs.filter(
    (run) => run.outcome === 'execution_failed' || (run.status === 'failed' && run.outcome === null),
  )
  const ungradedRuns = runs.filter(
    (run) => run.status === 'done' && run.outcome === null && !isAwaitingGrade(run, now),
  )
  const completedRuns = runs.filter(
    (run) => run.outcome === 'pass' || run.outcome === 'fail' || run.outcome === 'inconclusive',
  )
  const inconclusiveRuns = runs.filter((run) => run.outcome === 'inconclusive')
  const failureKinds = Object.keys(EXECUTION_FAILURE_KIND_LABEL) as ExecutionFailureKind[]
  const agentVersions = [...new Set(runs.map((run) => run.agent_version))].sort()
  const judges = [...new Set(runs.map(judgeOfRun).filter((judge) => judge !== null))]

  const recoveredAttempts = runs.flatMap((run) =>
    run.attempts.filter((entry) => entry.status !== 'completed').map((entry) => ({ run, entry })),
  )
  const interruptedCount = recoveredAttempts.filter(({ entry }) => entry.status === 'interrupted').length
  return (
    <>
      <LiveQueuePanel />

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Load</h2>
        <LoadOverTimeChart runs={runs} now={now} />
        <p className="text-sm text-muted-foreground">
          {interruptedCount} {interruptedCount === 1 ? 'attempt' : 'attempts'} interrupted ·{' '}
          {recoveredAttempts.length - interruptedCount} failed and retried ·{' '}
          {runs.filter((run) => run.status === 'failed').length} runs gave up after every attempt
        </p>
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Runs</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Count label="Completed" value={completedRuns.length} />
          <Count label="In Progress" value={inProgressRuns.length} />
          <Count
            label="Execution Failures"
            value={executionFailures.length}
            to={resultsUrl({ outcome: 'execution_failed' })}
          />
          <Count label="Not Graded" value={ungradedRuns.length} />
        </div>
        <RunHealthOverTimeChart runs={runs} now={now} />
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Execution failures by cause</h2>
        {executionFailures.length === 0 ? (
          <p className="text-sm text-muted-foreground">Every graded call ran properly.</p>
        ) : (
          <Table>
            <TableBody>
              {failureKinds.map((kind) => {
                const count = executionFailures.filter(
                  // Failed calls that were never graded have no kind yet, but the cause is known.
                  (run) => (run.execution_failure_kind ?? 'call_failed') === kind,
                ).length
                if (count === 0) return null
                return (
                  <TableRow key={kind}>
                    <TableCell>
                      <Link
                        to={resultsUrl({ outcome: 'execution_failed', execution_failure_kind: kind })}
                        className="hover:underline"
                      >
                        {EXECUTION_FAILURE_KIND_LABEL[kind]}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{count}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Evaluator</h2>
        <p className="text-sm text-muted-foreground">
          {judges.length === 0 ? 'No judge has graded a run yet.' : `Judges used: ${judges.join(', ')}.`}
        </p>
        {inconclusiveRuns.length === 0 ? (
          <p className="text-sm text-muted-foreground">No inconclusive runs.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {inconclusiveRuns.map((run) => (
              <li key={run.id}>
                <Link to={`/runs/${run.id}`} className="hover:underline">
                  <span className="text-muted-foreground">
                    {run.test_name} v{run.test_version}, agent {run.agent_version}:
                  </span>{' '}
                  {run.reason}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Call duration</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Agent</TableHead>
              <TableHead>Median</TableHead>
              <TableHead>Slowest</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {agentVersions.map((agentVersion) => {
              const finishedRuns = runs.filter(
                (run) => run.agent_version === agentVersion && run.status === 'done' && run.ended_at,
              )
              const slowest = finishedRuns.reduce<RunRow | null>(
                (current, run) => (!current || durationSeconds(run)! > durationSeconds(current)! ? run : current),
                null,
              )
              return (
                <TableRow key={agentVersion}>
                  <TableCell>{agentVersion}</TableCell>
                  <TableCell className="tabular-nums">
                    {formatSeconds(median(finishedRuns.map((run) => durationSeconds(run)!)))}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {slowest ? (
                      <Link to={`/runs/${slowest.id}`} className="hover:underline">
                        {formatRunDuration(slowest, now)}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        <p className="text-xs text-muted-foreground">Only calls that finished; failed calls end at the timeout.</p>
      </div>
    </>
  )
}
