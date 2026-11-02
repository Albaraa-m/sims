import { isActive, isAwaitingGrade } from '@/runs'
import type { RunRow } from '@/types'

// Only passes and fails say anything about the agent; the rest are system or evaluator problems.
// One judge is assumed: comparing grades from different judges is out of scope.
export function runsGradedOnAgentBehavior(runs: RunRow[]): RunRow[] {
  return runs.filter((run) => run.outcome === 'pass' || run.outcome === 'fail')
}

// A test's result for one agent version, from its graded runs.
export type SuiteStatus = 'passing' | 'flaky' | 'failing' | 'no_data'

// With fewer graded runs, a status is shown but not relied on.
export const MIN_RUNS_TO_RELY_ON = 3

export type SuiteCell = {
  pass: number
  fail: number
  status: SuiteStatus
  testId: string | null
}

export type SuiteChange = 'Broke' | 'Worse' | 'Better' | 'Fixed' | 'No change' | 'Too few runs' | "Can't compare"

export type SuiteRow = {
  lineageId: string
  testName: string
  // The latest version that ran; older versions' runs aren't counted.
  testId: string
  testVersion: number
  cells: Record<string, SuiteCell>
  change: SuiteChange | null
}

export function suiteStatusOf(pass: number, fail: number): SuiteStatus {
  if (pass + fail === 0) return 'no_data'
  if (fail === 0) return 'passing'
  if (pass === 0) return 'failing'
  return 'flaky'
}

export function isTooFewRuns(cell: SuiteCell): boolean {
  return cell.status !== 'no_data' && cell.pass + cell.fail < MIN_RUNS_TO_RELY_ON
}

// Higher is better: a fix moves up this order, a break moves down.
const STATUS_RANK: Record<SuiteStatus, number> = {
  no_data: -1,
  failing: 0,
  flaky: 1,
  passing: 2,
}

export function changeBetween(before: SuiteCell, after: SuiteCell): SuiteChange {
  if (before.status === 'no_data' || after.status === 'no_data') return "Can't compare"
  if (isTooFewRuns(before) || isTooFewRuns(after)) return 'Too few runs'
  if (after.status === before.status) return 'No change'
  if (after.status === 'passing') return 'Fixed'
  if (before.status === 'passing') return 'Broke'
  return STATUS_RANK[after.status] > STATUS_RANK[before.status] ? 'Better' : 'Worse'
}

// Changes first, bad then good, as they're what a comparison is for; then the rest.
const CHANGE_ORDER: SuiteChange[] = ['Broke', 'Worse', 'Fixed', 'Better', 'No change', 'Too few runs', "Can't compare"]

export function buildSuiteRows(runs: RunRow[], agentVersions: string[]): SuiteRow[] {
  const latestVersion = new Map<string, RunRow>()
  for (const run of runs) {
    const latest = latestVersion.get(run.test_lineage_id)
    if (!latest || run.test_version > latest.test_version) latestVersion.set(run.test_lineage_id, run)
  }
  const rows = [...latestVersion.values()].map((latest): SuiteRow => {
    const runsOfLatest = runs.filter((run) => run.test_id === latest.test_id)
    const cells = Object.fromEntries(
      agentVersions.map((agentVersion) => {
        const versionRuns = runsOfLatest.filter((run) => run.agent_version === agentVersion)
        const pass = versionRuns.filter((run) => run.outcome === 'pass').length
        const fail = versionRuns.filter((run) => run.outcome === 'fail').length
        return [
          agentVersion,
          {
            pass,
            fail,
            status: suiteStatusOf(pass, fail),
            testId: latest.test_id,
          },
        ]
      }),
    )
    const [before, after] = agentVersions
    return {
      lineageId: latest.test_lineage_id,
      testName: latest.test_name,
      testId: latest.test_id,
      testVersion: latest.test_version,
      cells,
      change: after ? changeBetween(cells[before], cells[after]) : null,
    }
  })
  const lastVersion = agentVersions.at(-1)
  // A test never graded on any version says nothing about the agent.
  const gradedRows = rows.filter((row) => Object.values(row.cells).some((cell) => cell.status !== 'no_data'))
  return gradedRows.sort(
    (a, b) =>
      (a.change ? CHANGE_ORDER.indexOf(a.change) : 0) - (b.change ? CHANGE_ORDER.indexOf(b.change) : 0) ||
      (lastVersion ? STATUS_RANK[a.cells[lastVersion].status] - STATUS_RANK[b.cells[lastVersion].status] : 0) ||
      a.testName.localeCompare(b.testName),
  )
}

// Where each simulation stands; every one is in exactly one bucket, so they add up.
export type LedgerBucket = 'finished' | 'in_flight' | 'execution_failure' | 'not_graded' | 'cancelled'

export function ledgerBucketOf(run: RunRow, now: number): LedgerBucket {
  if (run.status === 'cancelled') return 'cancelled'
  if (isActive(run)) return 'in_flight'
  if (run.outcome === 'execution_failed' || run.status === 'failed') return 'execution_failure'
  if (isAwaitingGrade(run, now)) return 'in_flight'
  if (run.outcome === null) return 'not_graded'
  return 'finished'
}

export function resultsUrl(filters: Record<string, string | number>): string {
  return `/results?${new URLSearchParams(Object.entries(filters).map(([key, value]) => [key, String(value)]))}`
}
