import type { AttemptLogEntry, ExecutionFailureKind, Outcome, RunRow, RunStatus, TestStatus } from '@/types'

export const startedAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export const RUN_STATUS_LABEL = {
  queued: 'Queued',
  running: 'Running',
  done: 'Done',
  // Never "Failed": that word is kept for the agent failing a test.
  failed: "Couldn't Run",
  cancelled: 'Cancelled',
} as const satisfies Record<RunStatus, string>

export const ATTEMPT_STATUS_LABEL = {
  completed: 'Completed',
  failed: 'Call Failed',
  interrupted: 'Interrupted',
} as const satisfies Record<AttemptLogEntry['status'], string>

// Waiting or running: what the pages keep polling for.
export function isActive(run: Pick<RunRow, 'status'>): boolean {
  return run.status === 'queued' || run.status === 'running'
}

export const TEST_STATUS_LABEL = {
  draft: 'Draft',
  ready: 'Ready',
} as const satisfies Record<TestStatus, string>

export const RUN_STATUS_BADGE_VARIANT = {
  queued: 'outline',
  running: 'outline',
  done: 'secondary',
  failed: 'destructive',
  cancelled: 'secondary',
} as const satisfies Record<RunStatus, string>

function formatSeconds(seconds: number): string {
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, '0')}s`
}

// The current attempt's call time; queue time isn't counted.
export function formatRunDuration(
  run: Pick<RunRow, 'status' | 'started_at' | 'call_started_at' | 'ended_at'>,
  now: number,
): string {
  if (run.status === 'queued') return '–'
  const start = Date.parse(run.call_started_at ?? run.started_at)
  const end = run.ended_at ? Date.parse(run.ended_at) : now
  return formatSeconds(Math.max(0, Math.round((end - start) / 1000)))
}

export function formatAttemptDuration(entry: AttemptLogEntry): string {
  if (!entry.started_at || !entry.ended_at) return '–'
  return formatSeconds(Math.max(0, Math.round((Date.parse(entry.ended_at) - Date.parse(entry.started_at)) / 1000)))
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
