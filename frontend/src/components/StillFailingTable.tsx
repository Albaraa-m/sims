import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { type ComparisonRow, resultsUrl } from '@/dashboard'

const ROWS_SHOWN_BEFORE_SHOW_ALL = 10

export default function StillFailingTable({ rows }: { rows: ComparisonRow[] }) {
  const [isShowingAll, setIsShowingAll] = useState(false)
  const navigate = useNavigate()

  // Newest agent version first, so "what still fails now" is at the top.
  const failingCells = rows
    .flatMap((row) =>
      Object.entries(row.cells).map(([agentVersion, cell]) => ({ row, agentVersion, cell })),
    )
    .filter(({ cell }) => cell.counts.fail > 0)
    .sort(
      (a, b) => b.agentVersion.localeCompare(a.agentVersion) || b.cell.counts.fail - a.cell.counts.fail,
    )
  if (failingCells.length === 0) return <p className="text-sm text-muted-foreground">No failed runs.</p>
  const shownCells = isShowingAll ? failingCells : failingCells.slice(0, ROWS_SHOWN_BEFORE_SHOW_ALL)

  return (
    <>
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead className="w-64">Test</TableHead>
            <TableHead className="w-16">Agent</TableHead>
            <TableHead className="w-16">Fails</TableHead>
            <TableHead>Latest reason</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shownCells.map(({ row, agentVersion, cell }) => {
            // Runs arrive newest first.
            const latestFailedRun = cell.runs.find((run) => run.outcome === 'fail')
            const { pass, fail } = cell.counts
            return (
              <TableRow
                key={`${row.testId}-${agentVersion}`}
                className="cursor-pointer"
                onClick={() =>
                  navigate(
                    resultsUrl({
                      test_id: row.testId,
                      test_version: row.testVersion,
                      agent_version: agentVersion,
                      outcome: 'fail',
                    }),
                  )
                }
              >
                <TableCell className="truncate">
                  {row.testName}{' '}
                  <span className="text-muted-foreground">
                    v{row.testVersion} · <span className="font-mono">{row.testId}</span>
                  </span>
                </TableCell>
                <TableCell>{agentVersion}</TableCell>
                <TableCell className="tabular-nums">
                  {fail}/{pass + fail}
                </TableCell>
                <TableCell className="truncate" title={latestFailedRun?.reason ?? undefined}>
                  {latestFailedRun?.reason}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {failingCells.length > ROWS_SHOWN_BEFORE_SHOW_ALL && (
        <Button variant="ghost" size="sm" onClick={() => setIsShowingAll(!isShowingAll)}>
          {isShowingAll ? 'Show fewer' : `Show all ${failingCells.length}`}
        </Button>
      )}
    </>
  )
}
