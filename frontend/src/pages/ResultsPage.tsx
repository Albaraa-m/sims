import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { listRunsOfAllTests, listTests } from '@/api'
import OutcomeBadge from '@/components/OutcomeBadge'
import Filter from '@/components/Filter'
import ScopeSelect from '@/components/ScopeSelect'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  EXECUTION_FAILURE_KIND_LABEL,
  isActive,
  isAwaitingGrade,
  OUTCOME_LABEL,
  RUN_STATUS_BADGE_VARIANT,
  RUN_STATUS_LABEL,
  startedAtFormat,
} from '@/runs'
import { isTestInScope, REGRESSION_SCOPE } from '@/scopes'
import type { ExecutionFailureKind, Outcome, RunRow, TestRow } from '@/types'

const POLL_INTERVAL_MS = 3000

export default function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tests, setTests] = useState<TestRow[]>([])
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)
  const navigate = useNavigate()

  const scope = searchParams.get('scope') ?? REGRESSION_SCOPE
  const filters = {
    test_id: searchParams.get('test_id') ?? '',
    agent_version: searchParams.get('agent_version') ?? '',
    outcome: searchParams.get('outcome') ?? '',
    // Filtered here rather than by the API; the dashboard links to these.
    test_version: searchParams.get('test_version') ?? '',
    execution_failure_kind: searchParams.get('execution_failure_kind') ?? '',
  }
  const setFilter = (name: keyof typeof filters, value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next)
  }

  useEffect(() => {
    listTests(true).then(setTests, (error: Error) => setLoadError(error.message))
  }, [])

  const loadRuns = useCallback(() => {
    listRunsOfAllTests({ ...Object.fromEntries(searchParams), scope }).then(
      (loadedRuns) => {
        setRuns(loadedRuns)
        setLoadedAt(Date.now())
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [searchParams, scope])

  useEffect(loadRuns, [loadRuns])

  const isPolling = runs?.some((run) => isActive(run) || isAwaitingGrade(run, loadedAt)) ?? false

  useEffect(() => {
    if (!isPolling) return
    const interval = setInterval(loadRuns, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [isPolling, loadRuns])

  const outcomes = Object.entries(OUTCOME_LABEL) as [Outcome, string][]
  const shownRuns = runs?.filter(
    (run) =>
      (!filters.test_version || String(run.test_version) === filters.test_version) &&
      (!filters.execution_failure_kind || run.execution_failure_kind === filters.execution_failure_kind),
  )
  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Simulations</h1>
      <div className="flex flex-wrap items-center gap-2">
        <ScopeSelect
          value={scope}
          onChange={(value) => {
            // A test from the old scope isn't in the new one.
            const next = new URLSearchParams(searchParams)
            next.set('scope', value)
            next.delete('test_id')
            next.delete('test_version')
            setSearchParams(next)
          }}
        />
        <Filter
          label="Test"
          value={filters.test_id}
          options={tests
            .filter((test) => isTestInScope(test, scope))
            .map((test) => ({ value: test.id, label: test.name }))}
          onChange={(value) => setFilter('test_id', value)}
        />
        <Filter
          label="Agent"
          value={filters.agent_version}
          options={['v1', 'v2'].map((version) => ({ value: version, label: `Agent ${version}` }))}
          onChange={(value) => setFilter('agent_version', value)}
        />
        <Filter
          label="Verdict"
          value={filters.outcome}
          options={outcomes.map(([value, label]) => ({ value, label }))}
          onChange={(value) => setFilter('outcome', value)}
        />
        {filters.test_version && (
          <Button variant="outline" size="sm" onClick={() => setFilter('test_version', '')}>
            Test version {filters.test_version} ✕
          </Button>
        )}
        {filters.execution_failure_kind && (
          <Button variant="outline" size="sm" onClick={() => setFilter('execution_failure_kind', '')}>
            {EXECUTION_FAILURE_KIND_LABEL[filters.execution_failure_kind as ExecutionFailureKind]} ✕
          </Button>
        )}
      </div>
      {loadError && <p className="text-sm text-destructive">Couldn't load results: {loadError}</p>}
      {shownRuns && shownRuns.length === 0 && <p className="text-sm text-muted-foreground">No simulations match these filters.</p>}
      {shownRuns && shownRuns.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Simulation</TableHead>
              <TableHead>When</TableHead>
              <TableHead>Test</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Verdict</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shownRuns.map((run) => (
              <TableRow key={run.id} onClick={() => navigate(`/simulations/${run.id}`)} className="cursor-pointer">
                <TableCell className="font-mono">
                  <Link to={`/simulations/${run.id}`}>{run.id}</Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{startedAtFormat.format(new Date(run.started_at))}</TableCell>
                <TableCell>
                  {run.test_name} <span className="text-muted-foreground">v{run.test_version}</span>
                </TableCell>
                <TableCell>{run.agent_version}</TableCell>
                <TableCell>
                  <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
                </TableCell>
                <TableCell>
                  <OutcomeBadge run={run} now={loadedAt} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}
