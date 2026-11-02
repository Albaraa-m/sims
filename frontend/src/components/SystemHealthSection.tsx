import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'

import { readQueueState } from '@/api'
import { FaultInjectionControls, HealthStatusBadge, QueueCard, WorkersCard } from '@/components/SystemHealthCards'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table'
import { type LedgerBucket, ledgerBucketOf, resultsUrl } from '@/dashboard'
import { EXECUTION_FAILURE_KIND_LABEL } from '@/runs'
import type { ExecutionFailureKind, QueueState, RunRow } from '@/types'

const POLL_INTERVAL_MS = 2000

const LEDGER_PILLS = [
  { bucket: 'finished', label: 'Finished', variant: 'outline' },
  { bucket: 'in_flight', label: 'In Flight', variant: 'info' },
  { bucket: 'execution_failure', label: 'Execution Failure', variant: 'serious' },
  { bucket: 'not_graded', label: 'Not Graded', variant: 'warning' },
  { bucket: 'cancelled', label: 'Cancelled', variant: 'neutral' },
] as const satisfies { bucket: LedgerBucket; label: string; variant: string }[]

function SimulationLedger({ runs, refused, now }: { runs: RunRow[]; refused: number; now: number }) {
  const counts = new Map<LedgerBucket, number>()
  for (const run of runs) {
    const bucket = ledgerBucketOf(run, now)
    counts.set(bucket, (counts.get(bucket) ?? 0) + 1)
  }
  const requested = runs.length + refused
  const settled = requested - (counts.get('in_flight') ?? 0)
  const unfinishedAttempts = runs.flatMap((run) => run.attempts.filter((entry) => entry.status !== 'completed'))
  const interrupted = unfinishedAttempts.filter((entry) => entry.status === 'interrupted').length

  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold">Every simulation accounted for</h2>
        <span className="ml-auto tabular-nums text-muted-foreground">
          {settled} of {requested} requested settled
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${requested ? (settled / requested) * 100 : 0}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        {LEDGER_PILLS.map(({ bucket, label, variant }) => {
          const pill = (
            <Badge variant={variant}>
              {counts.get(bucket) ?? 0} {label}
            </Badge>
          )
          return bucket === 'execution_failure' ? (
            <Link key={bucket} to={resultsUrl({ outcome: 'execution_failed' })}>
              {pill}
            </Link>
          ) : (
            <span key={bucket}>{pill}</span>
          )
        })}
        <Badge variant="neutral">{refused} Refused</Badge>
      </div>
      <p className="text-muted-foreground">
        Retried: {interrupted} {interrupted === 1 ? 'attempt' : 'attempts'} interrupted ·{' '}
        {unfinishedAttempts.length - interrupted} failed. A retry is the next attempt of the same simulation, so
        nothing is counted twice.
      </p>
    </div>
  )
}

function ExecutionFailuresByCause({ runs, now }: { runs: RunRow[]; now: number }) {
  const failures = runs.filter((run) => ledgerBucketOf(run, now) === 'execution_failure')
  const failureKinds = Object.keys(EXECUTION_FAILURE_KIND_LABEL) as ExecutionFailureKind[]
  return (
    <div className="space-y-2">
      <h2 className="text-base font-semibold">Execution failures by cause</h2>
      {failures.length === 0 ? (
        <p className="text-sm text-muted-foreground">Every settled simulation ran properly.</p>
      ) : (
        <Table>
          <TableBody>
            {failureKinds.map((kind) => {
              const count = failures.filter(
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
  )
}

export default function SystemHealthSection({ runs, now }: { runs: RunRow[]; now: number }) {
  const [state, setState] = useState<QueueState | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadState = useCallback(() => {
    readQueueState().then(
      (loadedState) => {
        setState(loadedState)
        setLoadError(null)
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [])

  useEffect(() => {
    loadState()
    const interval = setInterval(loadState, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [loadState])

  if (!state) return loadError ? <p className="text-sm text-destructive">Couldn't load the queue: {loadError}</p> : null

  return (
    <>
      <HealthStatusBadge state={state} />
      <div className="grid gap-4 md:grid-cols-2">
        <QueueCard state={state} />
        <WorkersCard state={state} onChange={loadState} />
      </div>
      <SimulationLedger runs={runs} refused={state.refused_simulations} now={now} />
      <ExecutionFailuresByCause runs={runs} now={now} />
      <FaultInjectionControls state={state} onChange={loadState} />
    </>
  )
}
