import { CircleCheckIcon, CircleDotIcon, CircleIcon, CircleSlashIcon } from 'lucide-react'
import type { ComponentType } from 'react'

import { Button } from '@/components/ui/button'
import { startedAtFormat } from '@/runs'
import type { SwarmRunStatus, SwarmRunSummary } from '@/types'

const RUN_STATUS_STYLE: Record<
  SwarmRunStatus,
  { label: string; className: string; Icon: ComponentType<{ className?: string }> }
> = {
  running: { label: 'Running', className: 'text-info', Icon: CircleDotIcon },
  queued: { label: 'Queued', className: 'text-neutral', Icon: CircleIcon },
  completed: { label: 'Completed', className: 'text-success', Icon: CircleCheckIcon },
  cancelled: { label: 'Cancelled', className: 'text-neutral', Icon: CircleSlashIcon },
}

export function SwarmRunStatusLabel({ status }: { status: SwarmRunStatus }) {
  const { label, className, Icon } = RUN_STATUS_STYLE[status]
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon className={`size-4 ${className} ${status === 'running' ? 'animate-pulse' : ''}`} />
      <span className="font-medium">{label}</span>
    </span>
  )
}

function summaryText(summary: SwarmRunSummary): string {
  const counts = summary.status_counts
  if (summary.status === 'running' || summary.status === 'queued') {
    const done = (counts.done ?? 0) + (counts.failed ?? 0)
    return `${done} of ${summary.total} done · ${counts.running ?? 0} running · ${counts.queued ?? 0} queued`
  }
  const outcomes = summary.outcome_counts
  const parts = [`${outcomes.pass ?? 0} pass`, `${outcomes.fail ?? 0} fail`]
  if (counts.cancelled) parts.push(`${counts.cancelled} cancelled`)
  if (counts.failed) parts.push(`${counts.failed} couldn't run`)
  return `${summary.total} calls · ${parts.join(' · ')}`
}

type SwarmRunListProps = {
  summaries: SwarmRunSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  onCancel: (id: string) => void
  cancellingId: string | null
}

// One row per press of Run swarm, newest first, like a CI system's list of workflow runs.
export default function SwarmRunList({ summaries, selectedId, onSelect, onCancel, cancellingId }: SwarmRunListProps) {
  return (
    <ul className="divide-y overflow-hidden rounded-lg border text-sm">
      {summaries.map((summary) => {
        const isSelected = summary.id === selectedId
        const isActive = summary.status === 'running' || summary.status === 'queued'
        return (
          <li
            key={summary.id}
            onClick={() => onSelect(summary.id)}
            className={`flex cursor-pointer items-center gap-4 px-4 py-2.5 ${
              isSelected ? 'bg-accent' : 'hover:bg-accent/50'
            }`}
          >
            <span className="w-28 shrink-0">
              <SwarmRunStatusLabel status={summary.status} />
            </span>
            <span className="w-24 shrink-0 font-medium">
              {summary.number > 0 ? `Run #${summary.number}` : 'Earlier runs'}
            </span>
            <span className="flex-1 text-muted-foreground">{summaryText(summary)}</span>
            <span className="text-muted-foreground">
              {summary.agent_versions.join(', ')}
              {summary.created_at && <> · {startedAtFormat.format(new Date(summary.created_at))}</>}
            </span>
            {isActive && summary.number > 0 && (
              <Button
                variant="outline"
                size="sm"
                disabled={cancellingId === summary.id}
                onClick={(event) => {
                  event.stopPropagation()
                  onCancel(summary.id)
                }}
              >
                {cancellingId === summary.id ? 'Cancelling…' : 'Cancel'}
              </Button>
            )}
          </li>
        )
      })}
    </ul>
  )
}
