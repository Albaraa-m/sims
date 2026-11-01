import type { RunRow, RunStatus } from '@/types'

export const startedAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

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
