import type { ExecutionFailureKind, Outcome, RunRow, RunStatus, TestStatus } from '@/types'

export const startedAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export const RUN_STATUS_LABEL = {
  running: 'Running',
  done: 'Done',
  failed: 'Failed',
} as const satisfies Record<RunStatus, string>

export const TEST_STATUS_LABEL = {
  draft: 'Draft',
  ready: 'Ready',
} as const satisfies Record<TestStatus, string>

export const RUN_STATUS_BADGE_VARIANT = {
  running: 'outline',
  done: 'secondary',
  failed: 'destructive',
} as const satisfies Record<RunStatus, string>

export function formatRunDuration(run: Pick<RunRow, 'started_at' | 'ended_at'>, now: number): string {
  const end = run.ended_at ? Date.parse(run.ended_at) : now
  const seconds = Math.max(0, Math.round((end - Date.parse(run.started_at)) / 1000))
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, '0')}s`
}

export const OUTCOME_LABEL = {
  pass: 'Pass',
  fail: 'Fail',
  inconclusive: 'Inconclusive',
  execution_failed: 'Execution Failure',
} as const satisfies Record<Outcome, string>

export const OUTCOME_BADGE_VARIANT = {
  pass: 'default',
  fail: 'destructive',
  inconclusive: 'outline',
  execution_failed: 'secondary',
} as const satisfies Record<Outcome, string>

export const EXECUTION_FAILURE_KIND_LABEL = {
  call_failed: 'Call Failed',
  call_unfinished: "Call Didn't Finish",
  no_report: 'No Session Report',
  no_recording: 'No Recording',
  agent_silent: 'Agent Never Spoke',
  caller_silent: 'Caller Never Spoke',
} as const satisfies Record<ExecutionFailureKind, string>

// Grading starts when the call ends and takes seconds; ungraded runs older than this
// predate the evaluator rather than waiting for it.
const GRADING_WINDOW_MS = 2 * 60 * 1000

export function isAwaitingGrade(run: Pick<RunRow, 'outcome' | 'ended_at'>, now: number): boolean {
  return run.outcome === null && run.ended_at !== null && now - Date.parse(run.ended_at) < GRADING_WINDOW_MS
}

export function turnElementId(turn: number): string {
  return `turn-${turn}`
}
