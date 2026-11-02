import { Link } from 'react-router'

import StillFailingTable from '@/components/StillFailingTable'
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  type ComparisonCell,
  countOutcomes,
  describeChange,
  groupRunsIntoComparisonRows,
  passRate,
  resultsUrl,
  runsGradedOnAgentBehavior,
} from '@/dashboard'
import type { RunRow } from '@/types'

function CellSummary({ cell, to }: { cell: ComparisonCell; to: string }) {
  const { pass, fail } = cell.counts
  if (cell.runs.length === 0) return <span className="text-muted-foreground">—</span>
  return (
    <Link to={to} className="tabular-nums hover:underline">
      {pass}/{pass + fail} pass
    </Link>
  )
}

export default function AgentQualityTab({ runs, judge }: { runs: RunRow[]; judge: string }) {
  const judgedRuns = runsGradedOnAgentBehavior(runs, judge)
  const agentVersions = [...new Set(judgedRuns.map((run) => run.agent_version))].sort()
  const rows = groupRunsIntoComparisonRows(judgedRuns, agentVersions)
  const [before, after] = agentVersions

  if (rows.length === 0) return <p className="text-sm text-muted-foreground">No graded runs for this judge yet.</p>

  return (
    <>
      <div className="space-y-2">
        <h2 className="text-base font-semibold">Version comparison</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Test</TableHead>
              {agentVersions.map((agentVersion) => (
                <TableHead key={agentVersion}>Agent {agentVersion}</TableHead>
              ))}
              {after && <TableHead>Change</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.testId}>
                <TableCell className="align-top">
                  <Link to={`/tests/${row.testId}`} className="hover:underline">
                    {row.testName}
                  </Link>{' '}
                  <span className="text-muted-foreground">
                    v{row.testVersion} · <span className="font-mono">{row.testId}</span>
                  </span>
                </TableCell>
                {agentVersions.map((agentVersion) => (
                  <TableCell key={agentVersion} className="align-top">
                    <CellSummary
                      cell={row.cells[agentVersion]}
                      to={resultsUrl({
                        test_id: row.testId,
                        test_version: row.testVersion,
                        agent_version: agentVersion,
                      })}
                    />
                  </TableCell>
                ))}
                {after && (
                  <TableCell className="align-top">
                    {describeChange(row.cells[before].counts, row.cells[after].counts)}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell>All tests</TableCell>
              {agentVersions.map((agentVersion) => {
                const counts = countOutcomes(judgedRuns.filter((run) => run.agent_version === agentVersion))
                const rate = passRate(counts)
                return (
                  <TableCell key={agentVersion} className="tabular-nums">
                    {rate === null
                      ? 'no graded runs'
                      : `${counts.pass}/${counts.pass + counts.fail} pass (${Math.round(rate * 100)}%)`}
                  </TableCell>
                )
              })}
              {after && <TableCell />}
            </TableRow>
          </TableFooter>
        </Table>
        <p className="text-xs text-muted-foreground">
          Counts only runs the judge passed or failed; execution failures, inconclusive and ungraded runs are on
          System health. Each cell is a few runs of one test version, so it shows how the agent handles these
          scenarios, not how it performs in general.
        </p>
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Still failing</h2>
        <StillFailingTable rows={rows} />
      </div>
    </>
  )
}
