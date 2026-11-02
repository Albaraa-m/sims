import type { RunRow } from '@/types'

const WINDOW_MS = 30 * 60 * 1000
const SAMPLES = 60
const CHART_HEIGHT_PX = 100

type Interval = { start: number; end: number }

// When each attempt of the run had a call in progress.
function callIntervals(run: RunRow, now: number): Interval[] {
  const logged = run.attempts
    .filter((entry) => entry.started_at && entry.ended_at)
    .map((entry) => ({ start: Date.parse(entry.started_at!), end: Date.parse(entry.ended_at!) }))
  if (run.status === 'running' && run.call_started_at) {
    logged.push({ start: Date.parse(run.call_started_at), end: now })
  }
  return logged
}

function contains(interval: Interval, time: number): boolean {
  return interval.start <= time && time < interval.end
}

// Calls running and waiting over the last 30 minutes, worked out from run timestamps.
export default function LoadOverTimeChart({ runs, now }: { runs: RunRow[]; now: number }) {
  const recentRuns = runs.filter((run) => now - Date.parse(run.started_at) < WINDOW_MS || run.status === 'running' || run.status === 'queued')
  if (recentRuns.length === 0) {
    return <p className="text-sm text-muted-foreground">No calls in the last 30 minutes.</p>
  }
  const firstRequest = Math.min(...recentRuns.map((run) => Date.parse(run.started_at)))
  const start = Math.max(firstRequest, now - WINDOW_MS)
  const step = Math.max((now - start) / SAMPLES, 1000)
  const times = Array.from({ length: SAMPLES }, (_, index) => start + index * step)

  const samples = times.map((time) => {
    let running = 0
    let queued = 0
    for (const run of recentRuns) {
      const requested = Date.parse(run.started_at)
      const finished = run.ended_at && !['queued', 'running'].includes(run.status) ? Date.parse(run.ended_at) : now
      if (time < requested || time >= finished) continue
      if (callIntervals(run, now).some((interval) => contains(interval, time))) running += 1
      else queued += 1
    }
    return { time, running, queued }
  })
  const interruptions = recentRuns.flatMap((run) =>
    run.attempts.filter((entry) => entry.status !== 'completed' && entry.ended_at).map((entry) => ({
      time: Date.parse(entry.ended_at!),
      kind: entry.status,
    })),
  )
  const peak = Math.max(1, ...samples.map((sample) => sample.running + sample.queued))
  const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' })

  return (
    <div className="space-y-2">
      <div className="relative flex items-end gap-px" style={{ height: CHART_HEIGHT_PX }}>
        {samples.map((sample) => (
          <div
            key={sample.time}
            className="flex flex-1 flex-col-reverse"
            title={`${timeFormat.format(sample.time)}: ${sample.running} running, ${sample.queued} queued`}
          >
            <div className="bg-[#2a78d6]" style={{ height: (sample.running / peak) * CHART_HEIGHT_PX }} />
            <div className="bg-[#2a78d6]/30" style={{ height: (sample.queued / peak) * CHART_HEIGHT_PX }} />
          </div>
        ))}
        {interruptions.map((mark, index) => (
          <div
            key={index}
            className={`absolute top-0 h-full w-0.5 ${mark.kind === 'interrupted' ? 'bg-[#d03b3b]' : 'bg-amber-500'}`}
            style={{ left: `${((mark.time - start) / (now - start || 1)) * 100}%` }}
            title={`${timeFormat.format(mark.time)}: attempt ${mark.kind === 'interrupted' ? 'interrupted' : 'failed, retried'}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span>{timeFormat.format(start)}</span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 bg-[#2a78d6]" /> Running
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 bg-[#2a78d6]/30" /> Queued
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-px bg-[#d03b3b]" /> Interrupted
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-px bg-amber-500" /> Failed, retried
        </span>
        <span className="ml-auto">now · peak {peak}</span>
      </div>
    </div>
  )
}
