import { Badge } from '@/components/ui/badge'
import {
  isAwaitingGrade,
  OUTCOME_BADGE_VARIANT,
  OUTCOME_LABEL,
  RUN_STATUS_BADGE_VARIANT,
  RUN_STATUS_LABEL,
} from '@/runs'
import type { RunRow } from '@/types'

type OutcomeBadgeProps = { run: Pick<RunRow, 'outcome' | 'ended_at' | 'status'>; now: number }

export default function OutcomeBadge({ run, now }: OutcomeBadgeProps) {
  if (run.outcome) return <Badge variant={OUTCOME_BADGE_VARIANT[run.outcome]}>{OUTCOME_LABEL[run.outcome]}</Badge>
  // No grade because there was no usable call, or the run was stopped.
  if (run.status === 'failed' || run.status === 'cancelled') {
    return <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
  }
  if (run.ended_at === null) return <span className="text-muted-foreground">–</span>
  return (
    <span className="text-muted-foreground">{isAwaitingGrade(run, now) ? 'Grading…' : 'Not Graded'}</span>
  )
}
