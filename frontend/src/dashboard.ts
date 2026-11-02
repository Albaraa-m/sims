import type { Outcome, RunRow } from '@/types'

export function judgeOfRun(run: RunRow): string | null {
  return run.judge_model && `${run.judge_model} · prompt ${run.judge_prompt_version ?? '?'}`
}

// Runs no judge looked at (execution failures, ungraded runs) belong to every judge's view.
export function runsSeenByJudge(runs: RunRow[], judge: string): RunRow[] {
  return runs.filter((run) => {
    const runJudge = judgeOfRun(run)
    return runJudge === null || runJudge === judge
  })
}

export function listJudgesNewestFirst(runs: RunRow[]): string[] {
  const judges = runs.map(judgeOfRun).filter((judge) => judge !== null)
  return [...new Set(judges)]
}

export type OutcomeCounts = Record<Outcome, number> & { ungraded: number }

export function countOutcomes(runs: RunRow[]): OutcomeCounts {
  const counts: OutcomeCounts = { pass: 0, fail: 0, inconclusive: 0, execution_failed: 0, ungraded: 0 }
  for (const run of runs) counts[run.outcome ?? 'ungraded'] += 1
  return counts
}

// Only passes and fails say anything about the agent.
export function passRate(counts: OutcomeCounts): number | null {
  const graded = counts.pass + counts.fail
  return graded === 0 ? null : counts.pass / graded
}

export type ComparisonCell = { runs: RunRow[]; counts: OutcomeCounts }

export type ComparisonRow = {
  testId: string
  testName: string
  testVersion: number
  cells: Record<string, ComparisonCell>
}

export function groupRunsIntoComparisonRows(runs: RunRow[], agentVersions: string[]): ComparisonRow[] {
  const rowsByTestId = new Map<string, ComparisonRow>()
  for (const run of runs) {
    let row = rowsByTestId.get(run.test_id)
    if (!row) {
      row = { testId: run.test_id, testName: run.test_name, testVersion: run.test_version, cells: {} }
      rowsByTestId.set(run.test_id, row)
    }
    ;(row.cells[run.agent_version] ??= { runs: [], counts: countOutcomes([]) }).runs.push(run)
  }
  const rows = [...rowsByTestId.values()]
  for (const row of rows) {
    for (const agentVersion of agentVersions) {
      const cell = (row.cells[agentVersion] ??= { runs: [], counts: countOutcomes([]) })
      cell.counts = countOutcomes(cell.runs)
    }
  }
  return rows.sort((a, b) => a.testName.localeCompare(b.testName) || b.testVersion - a.testVersion)
}

export type Change = 'Fixed' | 'Improved' | 'No change' | 'Regressed' | 'Broke' | "Can't compare"

export function describeChange(before: OutcomeCounts, after: OutcomeCounts): Change {
  const beforeRate = passRate(before)
  const afterRate = passRate(after)
  if (beforeRate === null || afterRate === null) return "Can't compare"
  if (beforeRate === 0 && afterRate === 1) return 'Fixed'
  if (beforeRate === 1 && afterRate === 0) return 'Broke'
  if (afterRate > beforeRate) return 'Improved'
  if (afterRate < beforeRate) return 'Regressed'
  return 'No change'
}

export function durationSeconds(run: RunRow): number | null {
  return run.ended_at ? (Date.parse(run.ended_at) - Date.parse(run.started_at)) / 1000 : null
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

export function resultsUrl(filters: Record<string, string | number>): string {
  return `/results?${new URLSearchParams(Object.entries(filters).map(([key, value]) => [key, String(value)]))}`
}
