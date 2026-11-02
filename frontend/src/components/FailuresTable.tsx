import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { type ComparisonRow, resultsUrl } from '@/dashboard'

const ROWS_SHOWN_BEFORE_SHOW_ALL = 10

export default function FailuresTable({ rows }: { rows: ComparisonRow[] }) {
  const [isShowingAll, setIsShowingAll] = useState(false)
  const navigate = useNavigate()

  // Newest agent version first, so failures of the current agent are at the top.
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
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Test</TableHead>
            <TableHead>Agent</TableHead>
            <TableHead>Fails</TableHead>
            <TableHead>Why it failed</TableHead>
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
                <TableCell className="align-top">
                  {row.testName}{' '}
                  <span className="text-muted-foreground">
                    v{row.testVersion} · <span className="font-mono">{row.testId}</span>
                  </span>
                </TableCell>
                <TableCell className="align-top">{agentVersion}</TableCell>
                <TableCell className="align-top tabular-nums">
                  {fail}/{pass + fail}
                </TableCell>
                <TableCell className="whitespace-normal">{latestFailedRun?.reason}</TableCell>
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
