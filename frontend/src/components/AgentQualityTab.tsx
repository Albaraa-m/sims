import { Link } from 'react-router'

import RunBlocks from '@/components/RunBlocks'
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  type ComparisonCell,
  countOutcomes,
  describeChange,
  groupRunsIntoComparisonRows,
  passRate,
  resultsUrl,
  runsSeenByJudge,
} from '@/dashboard'
import type { RunRow } from '@/types'

function CellSummary({ cell, to }: { cell: ComparisonCell; to: string }) {
  const { pass, fail, inconclusive, execution_failed, ungraded } = cell.counts
  if (cell.runs.length === 0) return <span className="text-muted-foreground">—</span>
  const rate = passRate(cell.counts)
  const notes = [
    inconclusive && `${inconclusive} inconclusive`,
    execution_failed && `${execution_failed} execution failure`,
    ungraded && `${ungraded} not graded`,
  ].filter(Boolean)
  return (
    <div className="space-y-1">
      <Link to={to} className="block tabular-nums hover:underline">
        {rate === null ? 'no graded runs' : `${pass}/${pass + fail} pass`}
      </Link>
      <RunBlocks runs={cell.runs} />
      {notes.length > 0 && <div className="text-xs text-muted-foreground">+ {notes.join(', ')}</div>}
    </div>
  )
}

export default function AgentQualityTab({ runs, judge }: { runs: RunRow[]; judge: string }) {
  const judgedRuns = runsSeenByJudge(runs, judge)
  const agentVersions = [...new Set(judgedRuns.map((run) => run.agent_version))].sort()
  const rows = groupRunsIntoComparisonRows(judgedRuns, agentVersions)
  const failedRuns = judgedRuns.filter((run) => run.outcome === 'fail')
  const [before, after] = agentVersions

  if (rows.length === 0) return <p className="text-sm text-muted-foreground">No runs yet. Start one from a test.</p>

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
          Pass rate counts only passes and fails. Each cell is a few runs of one test version, so it shows how the
          agent handles these scenarios, not how it performs in general.
        </p>
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Why runs failed</h2>
        {failedRuns.length === 0 && <p className="text-sm text-muted-foreground">No failed runs.</p>}
        {rows.map((row) => {
          const failedRunsOfRow = failedRuns.filter((run) => run.test_id === row.testId)
          if (failedRunsOfRow.length === 0) return null
          return (
            <div key={row.testId} className="space-y-1 text-sm">
              <h3 className="font-medium">
                {row.testName} <span className="text-muted-foreground">v{row.testVersion}</span>
              </h3>
              <ul className="space-y-1">
                {failedRunsOfRow.map((run) => (
                  <li key={run.id}>
                    <Link to={`/runs/${run.id}`} className="hover:underline">
                      <span className="text-muted-foreground">Agent {run.agent_version}:</span> {run.reason}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </>
  )
}
