import { useState } from 'react'

import { killWorker, setFailRate } from '@/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { QueueState } from '@/types'

const FAIL_RATES = [0, 0.1, 0.3, 0.5]
const QUEUE_ALMOST_FULL_SHARE = 0.8

type HealthStatus = { label: 'Healthy' | 'Degraded' | 'Down'; reasons: string[] }

function healthStatusOf(state: QueueState): HealthStatus {
  if (state.workers.length === 0) return { label: 'Down', reasons: ['No worker is running'] }
  const reasons: string[] = []
  if (state.stopped_workers.length > 0) {
    const count = state.stopped_workers.length
    reasons.push(`${count} ${count === 1 ? 'worker' : 'workers'} stopped`)
  }
  if (state.queued + state.running >= QUEUE_ALMOST_FULL_SHARE * state.max_queued) reasons.push('Queue almost full')
  if (state.refused_starts_last_hour > 0) reasons.push('Starts refused in the last hour')
  return { label: reasons.length > 0 ? 'Degraded' : 'Healthy', reasons }
}

const HEALTH_BADGE_VARIANT = {
  Healthy: 'success',
  Degraded: 'warning',
  Down: 'destructive',
} as const satisfies Record<HealthStatus['label'], string>

export function HealthStatusBadge({ state }: { state: QueueState }) {
  const status = healthStatusOf(state)
  return (
    <span className="flex items-center gap-2 text-sm">
      <Badge variant={HEALTH_BADGE_VARIANT[status.label]}>{status.label}</Badge>
      {status.reasons.length > 0 && <span className="text-muted-foreground">{status.reasons.join(' · ')}</span>}
    </span>
  )
}

function formatWait(seconds: number): string {
  const rounded = Math.round(seconds)
  return rounded < 60 ? `${rounded}s` : `${Math.floor(rounded / 60)}m ${String(rounded % 60).padStart(2, '0')}s`
}

function Meter({ label, used, limit, detail }: { label: string; used: number; limit: number; detail: string }) {
  return (
    <div className="grid grid-cols-[6rem_1fr_9rem] items-center gap-3">
      <span className="text-muted-foreground">{label}</span>
      <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${limit ? Math.min(1, used / limit) * 100 : 0}%` }}
        />
      </div>
      <span className="tabular-nums">{detail}</span>
    </div>
  )
}

export function QueueCard({ state }: { state: QueueState }) {
  const admitted = state.queued + state.running
  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <h2 className="text-base font-semibold">Queue</h2>
      <Meter
        label="Running"
        used={state.running}
        limit={state.max_running}
        detail={`${state.running} of ${state.max_running} slots`}
      />
      {/* Admission counts running simulations too, so waiting alone isn't measured against the limit. */}
      <Meter label="In queue" used={admitted} limit={state.max_queued} detail={`${admitted} of ${state.max_queued}`} />
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
        <span>
          Waiting <span className="text-foreground tabular-nums">{state.queued}</span>
        </span>
        <span>
          Longest wait{' '}
          <span className="text-foreground tabular-nums">
            {state.longest_wait_seconds === null ? '–' : formatWait(state.longest_wait_seconds)}
          </span>
        </span>
        <span>
          Refused in the last hour{' '}
          <span className="text-foreground tabular-nums">
            {state.refused_starts_last_hour} {state.refused_starts_last_hour === 1 ? 'start' : 'starts'}
          </span>
        </span>
      </div>
    </div>
  )
}

export function WorkersCard({ state, onChange }: { state: QueueState; onChange: () => void }) {
  const [actionError, setActionError] = useState<string | null>(null)
  const [killingWorkerId, setKillingWorkerId] = useState<string | null>(null)

  function kill(workerId: string) {
    setKillingWorkerId(workerId)
    setActionError(null)
    killWorker(workerId)
      .then(onChange, (error: Error) => setActionError(error.message))
      .finally(() => setKillingWorkerId(null))
  }

  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <h2 className="text-base font-semibold">Workers</h2>
      {state.workers.length === 0 && state.stopped_workers.length === 0 && (
        <p className="text-muted-foreground">No worker is running: waiting simulations start once one does.</p>
      )}
      <ul className="space-y-2">
        {state.workers.map((worker) => (
          <li key={worker.id} className="flex items-center gap-3">
            <span className="size-2 shrink-0 rounded-full bg-success" aria-label="Alive" />
            <div className="min-w-0">
              <div className="truncate font-mono">{worker.id}</div>
              <div className="text-muted-foreground tabular-nums">
                {worker.calls_running} of {worker.max_calls} simulations · heartbeat{' '}
                {Math.round(worker.heartbeat_seconds_ago)}s ago
              </div>
            </div>
            {state.fault_injection_enabled && (
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                disabled={killingWorkerId === worker.id}
                onClick={() => kill(worker.id)}
              >
                {killingWorkerId === worker.id ? 'Killing…' : 'Kill'}
              </Button>
            )}
          </li>
        ))}
        {state.stopped_workers.map((worker) => (
          <li key={worker.id} className="flex items-center gap-3">
            <span className="size-2 shrink-0 rounded-full bg-destructive" aria-label="Stopped" />
            <div className="min-w-0">
              <div className="truncate font-mono">{worker.id}</div>
              <div className="text-muted-foreground">
                Stopped ·{' '}
                {/* Only a live worker's reaper puts them back in the queue. */}
                {state.workers.length > 0
                  ? `back in queue within ${formatWait(worker.seconds_until_requeued)}`
                  : 'back in queue once a worker starts'}
              </div>
            </div>
            <Badge variant="warning" className="ml-auto">
              Recovering {worker.simulations_recovering}
            </Badge>
          </li>
        ))}
      </ul>
      {actionError && <p className="text-destructive">{actionError}</p>}
    </div>
  )
}

export function FaultInjectionControls({ state, onChange }: { state: QueueState; onChange: () => void }) {
  const [actionError, setActionError] = useState<string | null>(null)

  function changeFailRate(value: string) {
    setActionError(null)
    setFailRate(Number(value)).then(onChange, (error: Error) => setActionError(error.message))
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
      <span className="font-medium text-foreground">Fault injection</span>
      <span>Demo only: Kill a worker above, or make attempts fail before the call starts.</span>
      <Select value={String(state.fail_rate)} onValueChange={changeFailRate}>
        <SelectTrigger size="sm" aria-label="Inject failures" className="ml-auto">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {FAIL_RATES.map((rate) => (
            <SelectItem key={rate} value={String(rate)}>
              Fail {Math.round(rate * 100)}% of attempts
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {actionError && <p className="w-full text-destructive">{actionError}</p>}
    </div>
  )
}
