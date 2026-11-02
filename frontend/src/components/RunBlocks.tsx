import { Link } from 'react-router'

import { cn } from '@/lib/utils'
import { OUTCOME_LABEL } from '@/runs'
import type { Outcome, RunRow } from '@/types'

const BLOCK_CLASS = {
  pass: 'bg-primary',
  fail: 'bg-destructive',
  inconclusive: 'border border-muted-foreground',
  execution_failed: 'bg-muted-foreground/40',
} as const satisfies Record<Outcome, string>

// One block per run, so a small sample can't pass for a big one.
export default function RunBlocks({ runs }: { runs: RunRow[] }) {
  return (
    <div className="flex gap-0.5">
      {runs.map((run) => (
        <Link
          key={run.id}
          to={`/runs/${run.id}`}
          title={`${run.id}: ${run.outcome ? OUTCOME_LABEL[run.outcome] : 'not graded'}`}
          className={cn('size-3 rounded-sm', run.outcome ? BLOCK_CLASS[run.outcome] : 'bg-muted')}
        />
      ))}
    </div>
  )
}
