import { Badge } from '@/components/ui/badge'
import { isAwaitingGrade, OUTCOME_BADGE_VARIANT, OUTCOME_LABEL } from '@/runs'
import type { RunRow } from '@/types'

export default function OutcomeBadge({ run, now }: { run: Pick<RunRow, 'outcome' | 'ended_at'>; now: number }) {
  if (run.outcome) return <Badge variant={OUTCOME_BADGE_VARIANT[run.outcome]}>{OUTCOME_LABEL[run.outcome]}</Badge>
  if (run.ended_at === null) return <span className="text-muted-foreground">–</span>
  return (
    <span className="text-muted-foreground">{isAwaitingGrade(run, now) ? 'grading…' : 'not graded'}</span>
  )
}
