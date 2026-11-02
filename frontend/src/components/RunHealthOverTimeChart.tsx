import { isActive, isAwaitingGrade } from '@/runs'
import type { RunRow } from '@/types'

type Bucket = 'Completed' | 'Execution Failures' | 'Not Graded'

// Fixed order and colors, so a bucket keeps its color whatever the data.
const BUCKETS: { name: Bucket; className: string }[] = [
  { name: 'Completed', className: 'bg-[#2a78d6]' },
  { name: 'Execution Failures', className: 'bg-[#d03b3b]' },
  { name: 'Not Graded', className: 'bg-muted-foreground/40' },
]
const HOUR_MS = 60 * 60 * 1000
const DAY_MS = 24 * HOUR_MS
const CHART_HEIGHT_PX = 120

function bucketOfRun(run: RunRow, now: number): Bucket | null {
  if (isActive(run) || isAwaitingGrade(run, now)) return null
  if (run.outcome === 'execution_failed' || (run.status === 'failed' && run.outcome === null)) {
    return 'Execution Failures'
  }
  return run.outcome === null ? 'Not Graded' : 'Completed'
}

export default function RunHealthOverTimeChart({ runs, now }: { runs: RunRow[]; now: number }) {
  const startTimes = runs.map((run) => Date.parse(run.started_at))
  if (startTimes.length === 0) return null
  const first = Math.min(...startTimes)
  const last = Math.max(...startTimes)
  // Hourly within two days, daily beyond, so the bars stay readable.
  const step = last - first <= 2 * DAY_MS ? HOUR_MS : DAY_MS
  const firstSlot = Math.floor(first / step) * step
  const slots = Array.from({ length: Math.floor((last - firstSlot) / step) + 1 }, (_, index) => ({
    start: firstSlot + index * step,
    counts: { Completed: 0, 'Execution Failures': 0, 'Not Graded': 0 } as Record<Bucket, number>,
  }))
  for (const run of runs) {
    const bucket = bucketOfRun(run, now)
    if (bucket) slots[Math.floor((Date.parse(run.started_at) - firstSlot) / step)].counts[bucket] += 1
  }
  const tallest = Math.max(1, ...slots.map((slot) => Object.values(slot.counts).reduce((a, b) => a + b, 0)))
  const slotFormat = new Intl.DateTimeFormat(undefined, step === HOUR_MS ? { hour: 'numeric', day: 'numeric', month: 'short' } : { day: 'numeric', month: 'short' })

  return (
    <figure className="space-y-2 pt-4">
      <figcaption className="text-sm font-medium">
        Runs by start {step === HOUR_MS ? 'hour' : 'day'}{' '}
        <span className="font-normal text-muted-foreground">(tallest bar: {tallest})</span>
      </figcaption>
      <div className="flex gap-4 text-xs text-muted-foreground">
        {BUCKETS.map(({ name, className }) => (
          <span key={name} className="flex items-center gap-1.5">
            <span className={`size-2.5 rounded-sm ${className}`} />
            {name}
          </span>
        ))}
      </div>
      <div className="flex items-end gap-1 border-b" style={{ height: CHART_HEIGHT_PX }}>
        {slots.map((slot) => {
          const total = Object.values(slot.counts).reduce((a, b) => a + b, 0)
          const tooltip = [
            slotFormat.format(slot.start),
            ...BUCKETS.map(({ name }) => `${name}: ${slot.counts[name]}`),
          ].join('\n')
          return (
            <div key={slot.start} title={tooltip} className="flex h-full max-w-10 flex-1 flex-col-reverse gap-0.5">
              {BUCKETS.map(({ name, className }) =>
                slot.counts[name] > 0 ? (
                  <div
                    key={name}
                    className={`rounded-sm ${className}`}
                    style={{ height: `${(slot.counts[name] / tallest) * 100}%` }}
                  />
                ) : null,
              )}
              {total === 0 && <div className="h-px" />}
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{slotFormat.format(slots[0].start)}</span>
        {slots.length > 1 && <span>{slotFormat.format(slots[slots.length - 1].start)}</span>}
      </div>
    </figure>
  )
}
