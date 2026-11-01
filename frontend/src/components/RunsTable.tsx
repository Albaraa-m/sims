import { Link, useNavigate } from 'react-router'

import OutcomeBadge from '@/components/OutcomeBadge'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatRunDuration, RUN_STATUS_BADGE_VARIANT, startedAtFormat } from '@/runs'
import type { RunRow } from '@/types'

type RunsTableProps = {
  runs: RunRow[]
  // The version being viewed, to point out runs of other versions.
  viewedTestId: string
  now: number
}

export default function RunsTable({ runs, viewedTestId, now }: RunsTableProps) {
  const navigate = useNavigate()
  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No runs yet.</p>
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
          <TableHead>Time</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <TableRow key={run.id} onClick={() => navigate(`/runs/${run.id}`)} className="cursor-pointer">
            <TableCell className="font-mono">
              <Link to={`/runs/${run.id}`}>{run.id}</Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{startedAtFormat.format(new Date(run.started_at))}</TableCell>
            <TableCell>{run.agent_version}</TableCell>
            <TableCell className={run.test_id === viewedTestId ? '' : 'text-muted-foreground'}>
              v{run.test_version}
            </TableCell>
            <TableCell>
              <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{run.status}</Badge>
            </TableCell>
            <TableCell>
              <OutcomeBadge run={run} now={now} />
            </TableCell>
            <TableCell className="tabular-nums text-muted-foreground">{formatRunDuration(run, now)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
