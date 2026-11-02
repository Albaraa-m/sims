import { Link } from 'react-router'

import { ChangeLabel, StatusPill, SuiteStatusBar, SuiteStatusLegend } from '@/components/SuiteStatus'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { buildSuiteRows, MIN_RUNS_TO_RELY_ON, resultsUrl } from '@/dashboard'
import type { RunRow } from '@/types'

// The agent read as a test suite: each test counts once per version, by its runs' status.
export default function AgentQualityTab({ runs }: { runs: RunRow[] }) {
  const agentVersions = [...new Set(runs.map((run) => run.agent_version))].sort()
  const rows = buildSuiteRows(runs, agentVersions)
  const hasChange = agentVersions.length >= 2

  if (rows.length === 0) return <p className="text-sm text-muted-foreground">No graded runs yet.</p>

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-base font-semibold">Tests passing by agent version</h2>
        <div className="space-y-2">
          {agentVersions.map((agentVersion) => (
            <SuiteStatusBar
              key={agentVersion}
              label={`Agent ${agentVersion}`}
              cells={rows.map((row) => row.cells[agentVersion])}
            />
          ))}
        </div>
        <SuiteStatusLegend />
      </div>

      <div className="space-y-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Test</TableHead>
              {agentVersions.map((agentVersion) => (
                <TableHead key={agentVersion}>Agent {agentVersion}</TableHead>
              ))}
              {hasChange && <TableHead>Change</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.lineageId}>
                <TableCell>
                  <Link to={`/tests/${row.testId}`} className="hover:underline">
                    {row.testName}
                  </Link>{' '}
                  <span className="text-muted-foreground">v{row.testVersion}</span>
                </TableCell>
                {agentVersions.map((agentVersion) => (
                  <TableCell key={agentVersion}>
                    <StatusPill
                      cell={row.cells[agentVersion]}
                      to={resultsUrl({
                        test_id: row.testId,
                        test_version: row.testVersion,
                        agent_version: agentVersion,
                      })}
                    />
                  </TableCell>
                ))}
                {hasChange && row.change && (
                  <TableCell>
                    <ChangeLabel change={row.change} />
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="text-xs text-muted-foreground">
          Each test counts once per agent version, at its latest version. Passing: every graded run passed. Flaky: some
          passed. Failing: none did. n=1 or 2 marks fewer than {MIN_RUNS_TO_RELY_ON} graded runs, too few to rely on.
          Only passes and fails count; execution failures and inconclusive runs are on System health.{' '}
          <Link to={resultsUrl({ outcome: 'fail' })} className="underline">
            See every failed run
          </Link>
          .
        </p>
      </div>
    </div>
  )
}
