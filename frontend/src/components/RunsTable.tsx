import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react'
import { Fragment, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import OutcomeBadge from '@/components/OutcomeBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  ATTEMPT_STATUS_LABEL,
  formatAttemptDuration,
  formatRunDuration,
  RUN_STATUS_BADGE_VARIANT,
  RUN_STATUS_LABEL,
  startedAtFormat,
} from '@/runs'
import type { RunRow } from '@/types'

type RunsTableProps = {
  runs: RunRow[]
  // The version being viewed, to point out runs of other versions.
  viewedTestId: string
  now: number
}

// Only runs that were retried have earlier attempts worth expanding.
function wasRetried(run: RunRow): boolean {
  return run.attempts.some((entry) => entry.status !== 'completed')
}

export default function RunsTable({ runs, viewedTestId, now }: RunsTableProps) {
  const navigate = useNavigate()
  const [expandedRunIds, setExpandedRunIds] = useState<string[]>([])
  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No runs yet.</p>
  }

  function toggle(runId: string) {
    setExpandedRunIds(
      expandedRunIds.includes(runId) ? expandedRunIds.filter((id) => id !== runId) : [...expandedRunIds, runId],
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Run</TableHead>
          <TableHead>When</TableHead>
          <TableHead>Agent</TableHead>
          <TableHead>Test</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Outcome</TableHead>
          <TableHead>Attempts</TableHead>
          <TableHead>Time</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const isExpanded = expandedRunIds.includes(run.id)
          return (
            <Fragment key={run.id}>
              <TableRow onClick={() => navigate(`/runs/${run.id}`)} className="cursor-pointer">
                <TableCell className="font-mono">
                  <Link to={`/runs/${run.id}`}>{run.id}</Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {startedAtFormat.format(new Date(run.started_at))}
                </TableCell>
                <TableCell>{run.agent_version}</TableCell>
                <TableCell className={run.test_id === viewedTestId ? '' : 'text-muted-foreground'}>
                  v{run.test_version}
                </TableCell>
                <TableCell>
                  <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
                </TableCell>
                <TableCell>
                  <OutcomeBadge run={run} now={now} />
                </TableCell>
                <TableCell className="tabular-nums">
                  {wasRetried(run) ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto gap-1 px-1"
                      aria-expanded={isExpanded}
                      onClick={(event) => {
                        event.stopPropagation()
                        toggle(run.id)
                      }}
                    >
                      {isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
                      {Math.max(run.attempt, run.attempts.length)}
                    </Button>
                  ) : (
                    <span className="text-muted-foreground">{run.attempt || '–'}</span>
                  )}
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">{formatRunDuration(run, now)}</TableCell>
              </TableRow>
              {isExpanded &&
                run.attempts.map((entry) => (
                  <TableRow key={entry.attempt} className="bg-muted/40 text-muted-foreground">
                    <TableCell colSpan={4} className="pl-8">
                      Attempt {entry.attempt}
                    </TableCell>
                    <TableCell colSpan={3}>
                      {ATTEMPT_STATUS_LABEL[entry.status]}
                      {entry.reason && <> · {entry.reason}</>}
                    </TableCell>
                    <TableCell className="tabular-nums">{formatAttemptDuration(entry)}</TableCell>
                  </TableRow>
                ))}
            </Fragment>
          )
        })}
      </TableBody>
    </Table>
  )
}
