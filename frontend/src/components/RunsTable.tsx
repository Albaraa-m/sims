import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { RunRow, RunStatus } from '@/types'

const startedAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

const STATUS_BADGE_VARIANT = {
  running: 'outline',
  done: 'secondary',
  failed: 'destructive',
} as const satisfies Record<RunStatus, string>

function formatDuration(run: RunRow, now: number): string {
  const end = run.ended_at ? Date.parse(run.ended_at) : now
  const seconds = Math.max(0, Math.round((end - Date.parse(run.started_at)) / 1000))
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, '0')}s`
}

type RunsTableProps = {
  runs: RunRow[]
  // The version being viewed, to point out runs of other versions.
  viewedTestId: string
  now: number
}

export default function RunsTable({ runs, viewedTestId, now }: RunsTableProps) {
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
          <TableHead>Time</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <TableRow key={run.id}>
            <TableCell className="font-mono">{run.id}</TableCell>
            <TableCell className="text-muted-foreground">{startedAtFormat.format(new Date(run.started_at))}</TableCell>
            <TableCell>{run.agent_version}</TableCell>
            <TableCell className={run.test_id === viewedTestId ? '' : 'text-muted-foreground'}>
              v{run.test_version}
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_BADGE_VARIANT[run.status]}>{run.status}</Badge>
            </TableCell>
            <TableCell className="tabular-nums text-muted-foreground">{formatDuration(run, now)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
