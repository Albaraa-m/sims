import {
  ArrowDownIcon,
  ArrowUpIcon,
  CircleCheckIcon,
  CircleMinusIcon,
  CircleXIcon,
  TriangleAlertIcon,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { Link } from 'react-router'

import { isTooFewRuns, MIN_RUNS_TO_RELY_ON, type SuiteCell, type SuiteChange, type SuiteStatus } from '@/dashboard'

// The reserved status palette: green good, amber warning, red critical. A color never
// carries meaning alone; every status also has its icon and label.
const SUITE_STATUS_STYLE: Record<
  SuiteStatus,
  {
    label: string
    color: string
    Icon: ComponentType<{ className?: string; style?: React.CSSProperties }>
  }
> = {
  passing: { label: 'Passing', color: '#0ca30c', Icon: CircleCheckIcon },
  flaky: { label: 'Flaky', color: '#fab219', Icon: TriangleAlertIcon },
  failing: { label: 'Failing', color: '#d03b3b', Icon: CircleXIcon },
  no_data: { label: 'No data', color: '#c3c2b7', Icon: CircleMinusIcon },
}

// Worst first, as a reviewer reads them.
const SUITE_STATUSES: SuiteStatus[] = ['failing', 'flaky', 'passing', 'no_data']

export function StatusPill({ cell, to }: { cell: SuiteCell; to?: string }) {
  const { label, color, Icon } = SUITE_STATUS_STYLE[cell.status]
  const runs = cell.pass + cell.fail
  const content = (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-sm"
      style={{ backgroundColor: `${color}1f` }}
    >
      <Icon className="size-3.5 shrink-0" style={{ color }} />
      <span className="font-medium">{label}</span>
      {runs > 0 && (
        <span className="tabular-nums text-muted-foreground">
          {cell.pass}/{runs}
        </span>
      )}
      {isTooFewRuns(cell) && (
        <span className="text-muted-foreground" title={`Fewer than ${MIN_RUNS_TO_RELY_ON} graded runs`}>
          · n={runs}
        </span>
      )}
    </span>
  )
  return to && runs > 0 ? (
    <Link to={to} className="hover:opacity-80">
      {content}
    </Link>
  ) : (
    content
  )
}

const CHANGE_STYLE: Record<
  SuiteChange,
  {
    color: string | null
    Icon: ComponentType<{
      className?: string
      style?: React.CSSProperties
    }> | null
    strong: boolean
  }
> = {
  Fixed: { color: '#0ca30c', Icon: ArrowUpIcon, strong: true },
  Better: { color: '#0ca30c', Icon: ArrowUpIcon, strong: false },
  Broke: { color: '#d03b3b', Icon: ArrowDownIcon, strong: true },
  Worse: { color: '#d03b3b', Icon: ArrowDownIcon, strong: false },
  'No change': { color: null, Icon: null, strong: false },
  'Too few runs': { color: null, Icon: null, strong: false },
  "Can't compare": { color: null, Icon: null, strong: false },
}

export function ChangeLabel({ change }: { change: SuiteChange }) {
  const { color, Icon, strong } = CHANGE_STYLE[change]
  return (
    <span
      className={`inline-flex items-center gap-1 text-sm ${color ? (strong ? 'font-medium' : '') : 'text-muted-foreground'}`}
    >
      {Icon && color && <Icon className="size-3.5" style={{ color }} />}
      {change}
    </span>
  )
}

// One bar per agent version: how many tests are passing, flaky, failing or untested.
export function SuiteStatusBar({ label, cells }: { label: string; cells: SuiteCell[] }) {
  const total = cells.length
  const counts = Object.fromEntries(
    SUITE_STATUSES.map((status) => [status, cells.filter((cell) => cell.status === status).length]),
  ) as Record<SuiteStatus, number>
  const ordered: SuiteStatus[] = ['passing', 'flaky', 'failing', 'no_data']
  return (
    <div className="grid grid-cols-[6rem_1fr_auto] items-center gap-3 text-sm">
      <span className="font-medium">{label}</span>
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full bg-muted">
        {ordered
          .filter((status) => counts[status] > 0)
          .map((status) => (
            <div
              key={status}
              className="h-full first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${(counts[status] / total) * 100}%`,
                backgroundColor: SUITE_STATUS_STYLE[status].color,
              }}
              title={`${SUITE_STATUS_STYLE[status].label}: ${counts[status]} of ${total} tests`}
            />
          ))}
      </div>
      <span className="tabular-nums text-muted-foreground">
        <span className="font-medium text-foreground">{counts.passing}</span> of {total} passing
        {counts.flaky > 0 && <> · {counts.flaky} flaky</>}
        {counts.failing > 0 && <> · {counts.failing} failing</>}
      </span>
    </div>
  )
}

export function SuiteStatusLegend() {
  return (
    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
      {(['passing', 'flaky', 'failing', 'no_data'] as SuiteStatus[]).map((status) => {
        const { label, color, Icon } = SUITE_STATUS_STYLE[status]
        return (
          <span key={status} className="inline-flex items-center gap-1">
            <Icon className="size-3.5" style={{ color }} />
            {label}
          </span>
        )
      })}
    </div>
  )
}
